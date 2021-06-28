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

# Db den ilgili sorguyu çalıştırıp MessageQueue ya gönderecek metod, gerekli bilgiler parametrik ve os environment üzerinden aktarılır
async def perform_task(loop, sql_query=None, data_template_file_path=None, logger=None, config=None, consumer_pool_size=10, sql_fetch_size=1000):

    # Konfigürasyon bilgileri kontrol ediliyor, parametrik olarak gönderilmedi ise os environment içerisinden alınıyor
    if config is None:
        config = {
            "mq_host": os.environ.get('MQ_HOST'),
            "mq_port": int(os.environ.get('MQ_PORT', '5672')),
            "mq_vhost": os.environ.get('MQ_VHOST'),
            "mq_user": os.environ.get('MQ_USER'),
            "mq_pass": os.environ.get('MQ_PASS'),
            "mq_exchange": os.environ.get('MQ_EXCHANGE'),
            "mq_routing_key": os.environ.get('MQ_ROUTING_KEY'),
            "db_host": os.environ.get('DB_HOST'),
            "db_port": int(os.environ.get('DB_PORT', '5432')),
            "db_user": os.environ.get('DB_USER'),
            "db_pass": os.environ.get('DB_PASS'),
            "db_database": os.environ.get('DB_DATABASE'),
            "consumer_pool_size": os.environ.get("CONSUMER_POOL_SIZE"),
            "sql_query": os.environ.get('SQL_QUERY'),
            "sql_fetch_size": os.environ.get('SQL_FETCH_SIZE'),
            "data_template_file_path": os.environ.get('DATA_TEMPLATE_FILE_PATH')
        }

    # Sql sorgusu kontrol ediliyor, parametrik olarak gönderilmedi ise konfigürasyondan alınıyor
    if sql_query is None:
        sql_query = config.get("sql_query")

    # data_template kontrol ediliyor, parametrik olarak gönderilmedi ise konfigürasyondan alınıyor
    if data_template_file_path is None:
        data_template_file_path = config.get("data_template_file_path")

    # consumer_pool_size kontrol ediliyor, parametrik olarak gönderilmedi ise konfigürasyondan alınıyor
    if "consumer_pool_size" in config:
        if config.get("consumer_pool_size"):
            try:
                consumer_pool_size = int(config.get("consumer_pool_size"))
            except TypeError as e:
                if logger:
                    logger.error("Invalid pool size: %s" % (consumer_pool_size,))                
                raise e

    # sql_fetch_size kontrol ediliyor, parametrik olarak gönderilmedi ise konfigürasyondan alınıyor
    if "sql_fetch_size" in config:
        if config.get("sql_fetch_size"):
            try:
                sql_fetch_size = int(config.get("sql_fetch_size"))
            except TypeError as e:
                if logger:
                    logger.error("Invalid sql_fetch_size: %s" % (sql_fetch_size,))                
                raise e
    
    # routing_key kontrol ediliyor, parametrik olarak gönderilmedi ise konfigürasyondan alınıyor
    if "mq_routing_key" in config:
        if config.get("mq_routing_key"):
            try:
                mq_routing_key = str(config.get("mq_routing_key"))
            except TypeError as e:
                if logger:
                    logger.error("Invalid routing key!")                
                raise e

    # mq_exchange kontrol ediliyor, parametrik olarak gönderilmedi ise konfigürasyondan alınıyor
    if "mq_exchange" in config:
        if config.get("mq_exchange"):
            try:
                mq_exchange = str(config.get("mq_exchange"))
            except TypeError as e:
                if logger:
                    logger.error("Invalid exchange!")                
                raise e

    # data_template_file_path ile verilen dizindeki dosya içeriği okunuyor
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
    
    sql_query_offset = 0

    async def publish_to_rabbitmq(data, exchange, routing_key):
        await exchange.publish(aio_pika.Message(data.encode("utf-8")), routing_key= routing_key,)

    async def generate_jinja_template(template_content, valueDict):
        template = Template(template_content, enable_async=True)    
        return await template.render_async(valueDict)               
    
    async def get_channel() -> aio_pika.Channel:
        async with rabbitmq_channel_pool.acquire() as connection:
            return connection

    async def fetch_db_data():
        
        db_conn = await db_pool.acquire()
        cursor = await db_conn.cursor(cursor_factory= psycopg2.extras.RealDictCursor)

        channel = await get_channel()
        exchange = await channel.get_exchange(mq_exchange)

        nonlocal sql_query_offset
        is_continuous=True

        while is_continuous:
            try:    
                # Databaseden veriler çekiliyor     
                row_count=0     
                local_offset = sql_query_offset
                sql_query_offset += sql_fetch_size
                logger.debug(sql_query + f" offset {local_offset} limit {sql_fetch_size}")
                await cursor.execute(sql_query + f" offset {local_offset} limit {sql_fetch_size}")
                async for row in cursor:
                    # Alınan veri sayısı bulunuyor {cursor un row_count özelliği her db için desteklenmediğinden manual kontrol yapıldı}
                    row_count += 1
                    rendered_data = None
                    try:
                        # Jinja2 ile gelen row render edilip oluşan değer rendered_data ya aktarılıyor                    
                        rendered_data = await generate_jinja_template(data_template, row)            
                    except Exception as e:
                        if logger:
                            logger.error("Template Render Error: %s" % (e,))
                        await db_conn.close()
                        raise e            
                    
                    # Dönüştürülen veriler RabbitMq ya gönderiliyor
                    try:
                        await publish_to_rabbitmq(rendered_data, exchange, mq_routing_key)
                    except Exception as e:
                        if logger:
                            logger.error("Send To MQ Error: %s" % (e,))
                        await db_conn.close()
                        raise e
                
                if logger:
                        logger.error("row_count: %s" % (row_count,))

                # Eğer hiç veri alınamadıysa işlem tamamlanmış demektir döngü sonlandırılıyor
                if row_count == 0:
                    if logger:
                        logger.error("DB Content Empty: %s" % (row_count,))
                    await db_conn.close()
                    is_continuous=False
                    
            except Exception as e:
                if logger:
                    logger.error("DB Error: %s" % (e,))
                await db_conn.close()
                is_continuous=False
                
    async with rabbitmq_connection_pool, rabbitmq_channel_pool:
        consumer_pool = []
        if logger:
            logger.info("Consumers started")

        for _ in range(consumer_pool_size):
            consumer_pool.append(fetch_db_data())

        await asyncio.gather(*consumer_pool)
