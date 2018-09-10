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
        to_route = rkparts[0]
        from_route = rkparts[1]

    to_name = ' '.join([p.capitalize() for p in to_route.split('_')])
    from_name = ' '.join([p.capitalize() for p in from_route.split('_')])

    if type(message) is bytes:
        message = message.decode('utf-8')

    print("\n{0} [{1} <- {2}] {3}".format(timestamp(), to_name, from_name, message))


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


def get_routing_key(target, source) -> str:
    print("\nChatting with '" + target + "' as '" + source + "'")    
    return target + '.' + source


def main():
    amqp_uri = os.getenv('AMQP_URI', 'amqp://guest:guest@localhost:5672')

#    myname = getpass.getuser()

    toname = input("Chat with:")
    myname = input("Connect as:")

#    qname = myname.lower().replace(' ', '_')
#    my_route = qname + '.' + '#'

    my_name = myname.lower().replace(' ', '_')
    my_route = my_name + '.' + '#'
    routing_key = get_routing_key(toname, my_name)
    
    # Setup connection and channel
    cn = pika.BlockingConnection(pika.URLParameters(amqp_uri))
    ch = cn.channel()
    res = ch.queue_declare(queue="unchat_" + my_name, durable=True, auto_delete=False)

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
    start_consuming(cch, res.method.queue)

    # Go.
    print("Input '[to]:[message]' to switch target.")
    while True:
        try:
            i = input("> ").split(":", 1)
            if len(i) > 1:
                toname = i[0]
                routing_key = get_routing_key(toname, my_name)
                message = i[1]
            else:
                message = i[0]

            if message == "":
                continue

#            routing_key = toname + '.' + qname
            produce(ch, EXCHANGE, routing_key, myname, message)
            if toname != "all":
                print("{0} [{1} -> {2}] {3}".format(timestamp(), my_name.capitalize(), toname.capitalize(), message))

        except ValueError:
            print("Invalid input")

        except (KeyboardInterrupt, EOFError):
            print("\nAHHHH! YOU KILLED ME!")
            break

    cch.stop_consuming()
    sys.exit(0)

if __name__ == '__main__':
    main()
