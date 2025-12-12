"""
file namer. - Or a better name "Title Bot" to receive text an create a short
title
"""

from client import Client
from toolclient import ToolClient
from threading import Timer

# from bot_pipe import send_wait, print_content_response, print_payload_messages

def main():
    client = ClockBot()
    client.start()


class ClockBot(ToolClient):
    port = 9395
    # name = 'clock'
    delay = 3
    running = False

    def wake(self):
        print('Run wake')
        super().wake()

        if self.running:
            return

        self.tick = 0
        timer = Timer(self.delay, self.timer_tick)
        self.timer = timer
        self.running = True
        timer.daemon = True #allow keyboard interrupt.
        timer.start()

    def timer_tick(self):
        print('tick', self.tick)
        self.tick += 1
        self.perform_inner_work()
        self.timer.run()

    def perform_inner_work(self):
        # Run the inner job - the background counter to elicit historical
        # work

        # Tick add push date,

    def perform_work(self, message):
        """Memory sends a message to the llm, templated through the text file.
        The response is saved an a messsage is sent back to
        """
        print(f'[{self.get_name()}] start work')

    def easy_extract_message(self, d):
        return d['choices'][0]['message']['content']



if __name__ == "__main__":
    main()
