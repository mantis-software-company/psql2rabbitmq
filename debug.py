import os
import asyncio
import logging
from psql2rabbitmq_as_json import perform_task

if __name__ == "__main__":
    logger = logging.getLogger("psql2rabbitmq-as-json")
    logger.setLevel(os.environ.get('LOG_LEVEL', "DEBUG"))
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            os.environ.get('LOG_FORMAT', "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    )

    config = {
            "mq_host": 'rabbit.e-bus.svc.cluster.mantam',
            "mq_port": '5672',
            "mq_vhost": 'test',
            "mq_user": 'test',
            "mq_pass": 'test',
            "mq_exchange": 'umittest',
            "mq_routing_key": 'umittest',
            "db_host": 'trddb-20210111.trdizin.svc.cluster.mantam',
            "db_port": '5432',
            "db_user": 'trdizin',
            "db_pass": 'trdizin',
            "db_database": 'trdizinv4',
            "consumer_pool_size": "10",
            #"sql_query": 'Select * From  journal j Order By j.journal_id',
            "sql_query": 'Select * From  paper p Order By p.paper_id',
            "sql_fetch_size": '500',
            "data_template_file_path": '/home/uyilmaz/Desktop/psql2rabbitmq-as-json/data-template.tpl'
        }

    logger.addHandler(handler)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(perform_task(loop=loop, logger=logger, config=config))
    loop.close()