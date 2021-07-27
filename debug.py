import os
import asyncio
import logging
from psql2rabbitmq import perform_task

if __name__ == "__main__":
    logger = logging.getLogger("psql2rabbitmq")
    logger.setLevel(os.environ.get('LOG_LEVEL', "DEBUG"))
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            os.environ.get('LOG_FORMAT', "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    )

    config = {
            "mq_host": 'rabbit-address',
            "mq_port": '5672',
            "mq_vhost": 'your-vhost',
            "mq_user": 'your-username',
            "mq_pass": 'your-password',
            "mq_exchange": 'your-exchange',
            "mq_routing_key": 'your-routing-key',
            "db_host": 'your-db-host',
            "db_port": '5432',
            "db_user": 'your-db-username',
            "db_pass": 'your-db-password',
            "db_database": 'your-db',
            "sql_file_path": '/your-path/your-sql-query-file',
            "data_template_file_path": '/your-path/your-data-template-file',
            "consumer_pool_size": 1,
            "sql_fetch_size":10
        }

    logger.addHandler(handler)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(perform_task(loop=loop, logger=logger, config=config))
    finally:
        loop.close()