#!/usr/bin/env python
# unchat_cli - Very simple chat client.
import datetime
import getpass
import os
import pika
import sys
import threading

EXCHANGE = 'unchat'


def timestamp():
    return datetime.datetime.now().isoformat().split('.', 1)[0]


def consume(ch, method, params, message):
    from_route = 'unknown'

    rkparts = method.routing_key.split('.')

    # Get routing key components with some flexibility
    if len(rkparts) > 1:
        from_route = rkparts[1]

    from_name = ' '.join([p.capitalize() for p in from_route.split('_')])

    if type(message) is bytes:
        message = message.decode('utf-8')

    print("[{0}] << {1}: {2}".format(timestamp(), from_name,
                                       message))


def start_consuming(cch, queue):
    cch.basic_consume(consume, queue=queue, no_ack=True)
    th = threading.Thread(target=cch.start_consuming)
    th.start()
    th.join(0)


def produce(ch, exchange, routing_key, myname, message):
    if type(message) is str:
        message = message.encode()

    ch.basic_publish(
        exchange=exchange, routing_key=routing_key,
        properties=pika.spec.BasicProperties(content_type="text/plain"),
        body=message)


def main():
    amqp_uri = os.getenv('AMQP_URI', 'amqp://guest:guest@localhost:5672/')

    myname = getpass.getuser()

    cn = pika.BlockingConnection(pika.URLParameters(amqp_uri))
    ch = cn.channel()
    qname = myname.lower().replace(' ', '_')
    my_route = qname + '.' + '#'

    res = ch.queue_declare(queue=qname, durable=False, auto_delete=True)

    ch.exchange_declare(exchange=EXCHANGE, exchange_type='topic',
                        durable=True, passive=False)

    ch.queue_bind(exchange=EXCHANGE, queue=res.method.queue,
                  routing_key=my_route)
    ch.queue_bind(exchange=EXCHANGE, queue=res.method.queue,
                  routing_key='all.*')

    # Make a second connection for the thread to use
    ccn = pika.BlockingConnection(pika.URLParameters(amqp_uri))
    cch = ccn.channel()
    start_consuming(cch, res.method.queue)

    # Go.
    while True:
        try:

            i = input("[to] [message]: ")
            (toname, message) = i.split(' ', 1)
            routing_key = toname + '.' + qname
            produce(ch, EXCHANGE, routing_key, myname, message)

        except ValueError:
            print("Invalid input")

        except (KeyboardInterrupt, EOFError):
            print("\nAHHHH! YOU KILLED ME!")
            cch.stop_consuming()
            sys.exit(0)

if __name__ == '__main__':
    main()
