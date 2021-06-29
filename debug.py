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
            "sql_query": 'Select * From  your_table yt Order By yt.id',
            "data_template_file_path": '/your-path/data-template.tpl'
        }

    logger.addHandler(handler)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(perform_task(loop=loop, logger=logger, config=config))
    loop.close()