# psql2rabbitmq-as-json

psql2rabbitmq-as-json is a library that asynchronously forwards postgresql data to the RabbitMQ message queue in the requested template. Using the library, the parametrically given query is run, and the data obtained is converted into the format specified as a template and forwarded to the message queue.

## Installation

You can install this library easily with pip.
`pip install psql2rabbitmq-as-json` 

## Usage
### As a library
```py
import os
import asyncio
from psql2rabbitmq_as_json import perform_task

if __name__ == '__main__':
    logger = logging.getLogger("psql2rabbitmq-as-json")
    logger.setLevel(os.environ.get('LOG_LEVEL', "DEBUG"))
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            os.environ.get('LOG_FORMAT', "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    )
    logger.addHandler(handler)

    config = {
      "mq_host": os.environ.get('MQ_HOST'),
	    "mq_port": int(os.environ.get('MQ_PORT')), 
	    "mq_vhost": os.environ.get('MQ_VHOST'),
	    "mq_user": os.environ.get('MQ_USER'),
	    "mq_pass": os.environ.get('MQ_PASS'),
	    "mq_exchange": os.environ.get('MQ_EXCHANGE'),
      "mq_routing_key": os.environ.get('MQ_ROUTING_KEY'),
	    "db_host": os.environ.get('DB_HOST'),
	    "db_port": int(os.environ.get('DB_PORT')),
	    "db_user": os.environ.get('DB_USER'),
	    "db_pass": os.environ.get('DB_PASS'),
	    "db_database": os.environ.get('DB_DATABASE'),
      "consumer_pool_size": os.environ.get('CONSUMER_POOL_SIZE'),
      "sql_query": os.environ.get('SQL_QUERY'),
      "sql_fetch_size": os.environ.get('SQL_FETCH_SIZE'),
      "data_template_file_path": os.environ.get('DATA_TEMPLATE_FILE_PATH') 
    }
  
    sql_query = """Select * From your_table Where id>100 Order By id > %s;""" 
    data_template_file_path = """/usr/home/your_data_template_file""" 
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        perform_task(
          loop=loop,
          consumer_pool_size=10,
          sql_query=sql_query,
          config=config
        )
    )

loop.close()
```

This library uses [aio_pika](https://aio-pika.readthedocs.io/en/latest/), [aiopg](https://aiopg.readthedocs.io/en/stable/) and [jinja2](https://jinja2docs.readthedocs.io/en/stable/)packages.

### Standalone
You can also call this library as standalone job command.  Just set required environment variables and run `psql2rabbitmq-as-json`. This usecase perfectly fits when you need run it on cronjobs or kubernetes jobs. 

**Required environment variables:**
- MQ_HOST
- MQ_PORT (optional)
- MQ_VHOST
- MQ_USER
- MQ_PASS
- MQ_EXCHANGE
- MQ_ROUTING_KEY
- DB_HOST
- DB_PORT (optional)
- DB_USER
- DB_PASS
- DB_DATABASE
- SQL_QUERY (DB Select query. Ex: `Select * From your_table Where id > %s;`)
- DATA_TEMPLATE_FILE_PATH (File path contain reqested data template. Ex: `/usr/home/your_data_template_file`)
- CONSUMER_POOL_SIZE (optional, default value: 10)
- LOG_LEVEL (Logging level. See: [Python logging module docs](https://docs.python.org/3/library/logging.html#logging-levels))

**Example Kubernetes job:** 
 You can see it to [kube.yaml](kube.yaml)