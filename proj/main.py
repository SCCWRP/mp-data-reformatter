import pika, sys, os, json

if __name__ == '__main__':
    from reformat import full_reformat

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()

    channel.queue_declare(queue='mp_reformat')


    # The callback function will be the full reformatting routine
    def callback(ch, method, properties, body):
        print(" [x] Received %r" % body)
        args = json.loads(body)
        full_reformat(*[
            args['original_dir'], args['new_dir'], args['base_dir'], args['email']
        ])


    channel.basic_consume(queue='mp_reformat', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    main()