import aio_pika                             # pip install aio-pika
import aiopg                                # pip install aiopg
import psycopg2                             # pip install psycopg2
import psycopg2.extras                      
import jinja2                               # pip install Jinja2
import asyncio
import os
from jinja2 import Template                 
from aio_pika.pool import Pool              
import logging

# The method that will run the relevant query from the db and send it to the Message Queue, the necessary information is transferred via parametric and os environment.
async def perform_task(loop, sql_query=None, data_template_file_path=None, logger=None, config=None, consumer_pool_size=10, sql_fetch_size=1000):

    # Configuration information is checked, if it is not sent parametrically, it is retrieved from within the os environment.
    if config is None:
        config = {
            "mq_host": os.environ.get('MQ_HOST'),
            "mq_port": int(os.environ.get('MQ_PORT', '5672')),
            "mq_vhost": os.environ.get('MQ_VHOST'),
            "mq_user": os.environ.get('MQ_USER'),
            "mq_pass": os.environ.get('MQ_PASS'),
            "mq_exchange": os.environ.get('MQ_EXCHANGE', 'psql2rabbitmq'),
            "mq_routing_key": os.environ.get('MQ_ROUTING_KEY', 'psql2rabbitmq'),
            "db_host": os.environ.get('DB_HOST'),
            "db_port": int(os.environ.get('DB_PORT', '5432')),
            "db_user": os.environ.get('DB_USER'),
            "db_pass": os.environ.get('DB_PASS'),
            "db_database": os.environ.get('DB_DATABASE'),
            "sql_query": os.environ.get('SQL_QUERY'),
            "data_template_file_path": os.environ.get('DATA_TEMPLATE_FILE_PATH'),
            "consumer_pool_size": os.environ.get('CONSUMER_POOL_SIZE'),
            "sql_fetch_size": os.environ.get('SQL_FETCH_SIZE')
        }

    # The sql_query is checked, if it is not sent parametrically, it is taken from the configuration.
    if not sql_query and "sql_query" in config:
        sql_query = config.get("sql_query")    
    if not sql_query:
        if logger:
            logger.error("Invalid sql_query!")                
        return
    
    # The data_template_file_path is checked, if it is not sent parametrically, it is taken from the configuration.
    if not data_template_file_path and "data_template_file_path" in config:
        data_template_file_path = config.get("data_template_file_path")    
    if not data_template_file_path:
        if logger:
            logger.error("Invalid data_template_file_path!")                
        return
    
    # The routing_key is checked, if it is not sent parametrically, it is taken from the configuration.
    if "mq_routing_key" in config:                    
        mq_routing_key = str(config.get("mq_routing_key"))
    if not mq_routing_key:
        if logger:
            logger.error("Invalid mq_routing_key!")                
        return

    # The mq_exchange is checked, if it is not sent parametrically, it is taken from the configuration.
    if "mq_exchange" in config:
        mq_exchange = str(config.get("mq_exchange"))
    if not mq_exchange:
        if logger:
            logger.error("Invalid mq_exchange!")                
        return

    # The consumer_pool_size is checked, if it is exist in the configuration than overriding value from the configuration.
    if "consumer_pool_size" in config:
        try:
            pool_size = int(config.get("consumer_pool_size"))
            consumer_pool_size = pool_size
        except Exception as e:
            if logger:
                logger.error("CONSUMER_POOL_SIZE in config is not available: {} -> {}".format(config.get("consumer_pool_size"), e))
    
    # The consumer_pool_size is checked, if it is exist in the configuration than overriding value from the configuration.
    if "sql_fetch_size" in config:
        try:
            fetch_size = int(config.get("sql_fetch_size"))
            sql_fetch_size = fetch_size
        except Exception as e:
            if logger:
                logger.error("SQL_FETCH_SIZE in config is not available: {} -> {}".format(config.get("sql_fetch_size"), e))

    # Reading the file content in the directory given with data_template_file_path.
    data_template_file = open(data_template_file_path, "r")
    data_template = data_template_file.read()

    db_pool = await aiopg.create_pool(
        host=config.get("db_host"),
        user=config.get("db_user"),
        password=config.get("db_pass"),
        database=config.get("db_database"),
        port=config.get("db_port"),
        minsize=consumer_pool_size,
        maxsize=consumer_pool_size * 2
    )

    async def get_rabbitmq_channel():
        async with rabbitmq_connection_pool.acquire() as connection:
            return await connection.channel()
    
    async def get_rabbitmq_connection():
        return await aio_pika.connect(
            host=config.get("mq_host"),
            port=config.get("mq_port"),
            login=config.get("mq_user"),
            password=config.get("mq_pass"),
            virtualhost=config.get("mq_vhost"),
            loop=loop
        )

    rabbitmq_connection_pool = Pool(get_rabbitmq_connection, max_size=consumer_pool_size, loop=loop)
    rabbitmq_channel_pool = Pool(get_rabbitmq_channel, max_size=consumer_pool_size, loop=loop)
    
    # The variable that holds the next offset value for each asynchronous method.
    # The methods determine the next dataset over this shared variable. 
    sql_query_offset = 0
          
    async def fetch_db_data(methodId):

        nonlocal sql_query_offset
        template = Template(data_template, enable_async=True)   
        
        async with db_pool.acquire() as db_conn:
            async with db_conn.cursor(cursor_factory= psycopg2.extras.RealDictCursor) as cursor:
                async with rabbitmq_channel_pool.acquire() as channel:
                    
                    exchange = await channel.get_exchange(mq_exchange)
        
                    while True:
                        try:    
                            # Retrieving data from database
                            local_offset = sql_query_offset
                            sql_query_offset += sql_fetch_size
                            
                            if logger:
                                logger.debug(f"Method-{methodId} => " + sql_query + f" offset {local_offset} limit {sql_fetch_size}")

                            await cursor.execute(sql_query + f" offset {local_offset} limit {sql_fetch_size}")
                            async for row in cursor:  
                                try:                  
                                    # The fetched row is rendered and the resulting value is transferred to rendered_data.
                                    rendered_data = await template.render_async(row)                        
                                    
                                    # Sending rendered_data to RabbitMq
                                    await exchange.publish(aio_pika.Message(rendered_data.encode("utf-8")), routing_key= mq_routing_key,)                        
                                except Exception as e:
                                    if logger:
                                        logger.error("Row Send Error: {} -> {}".format(rendered_data, e))
                            
                            if logger:
                                    logger.debug(f"Method-{methodId} => row_count: {cursor.rowcount}")

                            # If no data is received, the process is complete, and the loop is terminated.
                            if cursor.rowcount == 0:
                                if logger:
                                    logger.info(f"Method-{methodId} has finished.")
                                break    
                
                        except Exception as e:
                            if logger:
                                logger.error("Error: %s" % (e,))
                            break
                
    async with rabbitmq_connection_pool, rabbitmq_channel_pool:
        consumer_pool = []
        if logger:
            logger.info("The Psql2RabbitMq transfer process has started.")

        for id in range(consumer_pool_size):
            consumer_pool.append(fetch_db_data(id))

        await asyncio.gather(*consumer_pool)
