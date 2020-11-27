# INFO
# There is a container called reformat-mq, whose docker file is in the rabbitmq folder in this same project directory
# There is the rabbitmq container running on this host machine also, which acts as the rabbit mq server
# The upload.py script checks if the user entered their email or not.
#    If they did, the script sends the relevant information to the rabbitmq server via the mp_reformat queue
# This script acts as the "consumer" The reformat-mq script runs this main.py script and listens for messages
#    coming in from the rabbitmq server, on the mp_reformat queue

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
            args['original_dir'], args['new_dir'], args['base_dir'], args['email'], args['sessionid']
        ])


    channel.basic_consume(queue='mp_reformat', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    main()