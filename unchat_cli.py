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


def to_snake_case(text: str) -> str:
    return text.lower().replace(' ', '_')


def to_title_case(text: str) -> str:
    return ' '.join([p.capitalize() for p in text.split('_')])


def generate_consume(queue_name):
    def consume(ch, method, params, message):
        from_route = 'unknown'

        rkparts = method.routing_key.split('.')

        # Get routing key components with some flexibility
        if len(rkparts) > 1:
            to_route = rkparts[0]
        from_route = rkparts[1]

        if from_route == queue_name:
            return

        if type(message) is bytes:
            message = message.decode('utf-8')

        print("\n{0} [{1} <- {2}] {3}\n> ".format(timestamp(),
                                                  to_title_case(to_route),
                                                  to_title_case(from_route),
                                                  message), end='')
    return consume


def start_consuming(cch, queue, my_name):
    cch.basic_consume(generate_consume(my_name), queue=queue, no_ack=True)
    th = threading.Thread(target=cch.start_consuming)
    th.start()
    th.join(0)


def produce(ch, exchange, routing_key, message):
    if type(message) is str:
        message = message.encode()

    ch.basic_publish(
        exchange=exchange, routing_key=routing_key,
        properties=pika.spec.BasicProperties(content_type="text/plain"),
        body=message)


def get_routing_key(target, source) -> str:
    print("\nChatting with '" + to_title_case(target) + "' as '" + to_title_case(source) + "'")
    return target + '.' + source


def main():
    amqp_uri = os.getenv('AMQP_URI', 'amqp://guest:guest@localhost:5672/')

    to_name = to_snake_case(input("Chat with:"))
    my_name = to_snake_case(input("Connect as:"))

    my_route = my_name + '.' + '#'
    routing_key = get_routing_key(to_name, my_name)

    # Setup connection and channel
    cn = pika.BlockingConnection(pika.URLParameters(amqp_uri))
    ch = cn.channel()
    res = ch.queue_declare(queue="unchat_" + my_name, durable=False, auto_delete=True)

    # Declare queue and setup bindings
    ch.exchange_declare(exchange=EXCHANGE, exchange_type='topic',
                        durable=True, passive=False)

    ch.queue_bind(exchange=EXCHANGE, queue=res.method.queue,
                  routing_key=my_route)
    ch.queue_bind(exchange=EXCHANGE, queue=res.method.queue,
                  routing_key='all.*')

    # Make a second connection for the consuming thread to use
    ccn = pika.BlockingConnection(pika.URLParameters(amqp_uri))
    cch = ccn.channel()
    start_consuming(cch, res.method.queue, my_name)

    # Go.
    print("Input '[to]:[message]' to switch target.")
    while True:
        try:
            i = input("> ").split(":", 1)
            if len(i) > 1:
                to_name = i[0].lower().replace(' ', '_')
                routing_key = get_routing_key(to_name, my_name)
                message = i[1]
            else:
                message = i[0]

            if message == "":
                continue

            if cn.is_open is not True:
                cn = pika.BlockingConnection(pika.URLParameters(amqp_uri))
                ch = None

            if ch is None or ch.is_open is not True:
                ch = cn.channel()

            rets = 5
            while rets > 0:
                try:
                    produce(ch, EXCHANGE, routing_key, message)
                    break
                except pika.exceptions.ConnectionClosed:
                    cn = pika.BlockingConnection(pika.URLParameters(amqp_uri))
                    ch = cn.channel()

            if rets == 0:
                print("\nCan not sent!  Dying!")
                raise EOFError()

            if to_name != "all":
                print("{0} [{1} -> {2}] {3}".format(timestamp(),
                                                    to_title_case(my_name),
                                                    to_title_case(to_name),
                                                    message))

        except ValueError:
            print("Invalid input")

        except (KeyboardInterrupt, EOFError):
            print("\nAHHHH! YOU KILLED ME!")
            break

    cch.stop_consuming()
    sys.exit(0)

if __name__ == '__main__':
    main()
