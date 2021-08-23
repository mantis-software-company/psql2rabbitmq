import aio_pika  # pip install aio-pika
import aiopg  # pip install aiopg
import psycopg2  # pip install psycopg2
import psycopg2.extras
import jinja2  # pip install Jinja2
import asyncio
import os
from jinja2 import Template
from aio_pika.pool import Pool
import logging
import json
import datetime


# The method that will run the relevant query from the db and send it to the Message Queue, the necessary information is transferred via parametric and os environment.
async def perform_task(loop, sql_file_path=None, data_template_file_path=None, logger=None, config=None,
                       consumer_pool_size=10, sql_fetch_size=1000):
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
            "sql_file_path": os.environ.get('SQL_FILE_PATH'),
            "data_template_file_path": os.environ.get('DATA_TEMPLATE_FILE_PATH'),
            "consumer_pool_size": os.environ.get('CONSUMER_POOL_SIZE'),
            "sql_fetch_size": os.environ.get('SQL_FETCH_SIZE')
        }

    logger.debug("Config:")
    logger.debug(config)

    sql_query = None
    # The data_template_file_path is checked, if it is not sent parametrically, it is taken from the configuration.
    if not sql_file_path and "sql_file_path" in config:
        sql_file_path = config.get("sql_file_path")
        logger.debug(f"{'sql_file_path':<23} assigned to : {sql_file_path}")
    if not sql_file_path:
        if logger:
            logger.error("Invalid sql_file_path!")
        return

    # The data_template_file_path is checked, if it is not sent parametrically, it is taken from the configuration.
    if not data_template_file_path and "data_template_file_path" in config:
        data_template_file_path = config.get("data_template_file_path")
        logger.debug(f"{'data_template_file_path':<23} assigned to : {data_template_file_path}")
    if not data_template_file_path:
        if logger:
            logger.error("Invalid data_template_file_path!")
        return

    # The routing_key is checked, if it is not sent parametrically, it is taken from the configuration.
    if "mq_routing_key" in config:
        mq_routing_key = str(config.get("mq_routing_key"))
        logger.debug(f"{'mq_routing_key':<23} assigned to : {mq_routing_key}")
    if not mq_routing_key:
        if logger:
            logger.error("Invalid mq_routing_key!")
        return

    # The mq_exchange is checked, if it is not sent parametrically, it is taken from the configuration.
    if "mq_exchange" in config:
        mq_exchange = str(config.get("mq_exchange"))
        logger.debug(f"{'mq_exchange':<23} assigned to : {mq_exchange}")
    if not mq_exchange:
        if logger:
            logger.error("Invalid mq_exchange!")
        return

    # The consumer_pool_size is checked, if it is exist in the configuration than overriding value from the configuration.
    if "consumer_pool_size" in config:
        try:
            pool_size = int(config.get("consumer_pool_size"))
            consumer_pool_size = pool_size
            logger.debug(f"{'consumer_pool_size':<23} assigned to : {consumer_pool_size}")
        except Exception as e:
            if logger:
                logger.error(
                    "CONSUMER_POOL_SIZE in config is not available: {} -> {}".format(config.get("consumer_pool_size"),
                                                                                     e))

    # The consumer_pool_size is checked, if it is exist in the configuration than overriding value from the configuration.
    if "sql_fetch_size" in config:
        try:
            fetch_size = int(config.get("sql_fetch_size"))
            sql_fetch_size = fetch_size
            logger.debug(f"{'sql_fetch_size':<23} assigned to : {sql_fetch_size}")
        except Exception as e:
            if logger:
                logger.error(
                    "SQL_FETCH_SIZE in config is not available: {} -> {}".format(config.get("sql_fetch_size"), e))

    # Reading the file content in the directory given with sql_file_path.
    sql_file = open(sql_file_path, "r")
    sql_query = sql_file.read()

    logger.debug("sql_query:")
    logger.debug(sql_query)

    # Reading the file content in the directory given with data_template_file_path.
    data_template_file = open(data_template_file_path, "r")
    data_template = data_template_file.read()

    db_host = config.get("db_host")
    db_user = config.get("db_user")
    db_pass = config.get("db_pass")
    db_database = config.get("db_database")
    db_port = config.get("db_port")

    logger.debug(f"{'db_host':<12} assigned to : {db_host}")
    logger.debug(f"{'db_user':<12} assigned to : {db_user}")
    logger.debug(f"{'db_pass':<12} assigned to : {db_pass}")
    logger.debug(f"{'db_database':<12} assigned to : {db_database}")
    logger.debug(f"{'db_port':<12} assigned to : {db_port}")

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

        # async with db_pool.acquire() as db_conn:
        #     async with db_conn.cursor(cursor_factory= psycopg2.extras.RealDictCursor) as cursor:
        # async with rabbitmq_channel_pool.acquire() as channel:                    
        #     exchange = await channel.get_exchange(mq_exchange)

        while True:
            try:
                # Retrieving data from database
                local_offset = sql_query_offset
                sql_query_offset += sql_fetch_size

                if "{{offset}}" in sql_query:
                    sql_query_full = sql_query.replace("{{offset}}", str(local_offset))
                else:
                    sql_query_full = sql_query + f" offset {local_offset}"

                if "{{limit}}" in sql_query_full:
                    sql_query_full = sql_query_full.replace("{{limit}}", str(sql_fetch_size))
                else:
                    sql_query_full = sql_query_full + f" limit {sql_fetch_size}"

                if logger:
                    logger.debug(f"entered into Method-{methodId}")

                dsn = "host=%s user=%s password=%s dbname=%s port=%s" % (
                db_host, db_user, db_pass, db_database, db_port)
                async with aiopg.connect(dsn=dsn, timeout=1200) as db_conn:

                    if logger:
                        logger.debug('db connection opened')

                    async with db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:

                        if logger:
                            logger.debug('db cursor opened')

                        await cursor.execute(sql_query_full)
                        response = await cursor.fetchall()

                        if logger:
                            logger.info(f"Method-{methodId} => offset: {local_offset} limit: {sql_fetch_size}")

                        if cursor.rowcount is not None and cursor.rowcount > 0:
                            async with rabbitmq_channel_pool.acquire() as channel:
                                if logger:
                                    logger.debug('rabbitmq channel acquired')

                                exchange = await channel.get_exchange(mq_exchange)

                                if logger:
                                    logger.debug('rabbitmq exchange acquired')

                                try:
                                    for row in response:
                                        try:
                                            # The fetched row is rendered and the resulting value is transferred to rendered_data.
                                            rendered_data = await template.render_async(row, json=json,
                                                                                        datetime=datetime)
                                            # print(rendered_data)
                                            # Sending rendered_data to RabbitMq
                                            await exchange.publish(aio_pika.Message(rendered_data.encode("utf-8")),
                                                                   routing_key=mq_routing_key, )
                                            if logger:
                                                logger.debug('message submitted to mq!!!')

                                        except Exception as e:
                                            if logger:
                                                logger.error("Row Send Error: {} -> {}".format(rendered_data, e))

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
                    raise e
                break

    async with rabbitmq_connection_pool, rabbitmq_channel_pool:
        consumer_pool = []
        if logger:
            logger.info("The Psql2RabbitMq transfer process has started.")

        for id in range(consumer_pool_size):
            consumer_pool.append(fetch_db_data(id))

        await asyncio.gather(*consumer_pool)
