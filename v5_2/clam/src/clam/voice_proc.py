from multiprocessing import Process, Pipe
import time
from .vibevoice_say import async_run

def main():
    # Create a pipe (returns two connection objects)
    p, (parent_conn, child_conn) = start_worker()
    # Send a message through the pipe
    while True:
        try:
            value = input('> ')
            parent_conn.send(value)
        except KeyboardInterrupt:
            print('exit')
            break
        print("Message sent to worker")
    # Wait for process to complete
    p.join()
    print("Worker finished")

def start_worker():
    parent_conn, child_conn = Pipe()

    # Start the process
    p = Process(target=worker, args=(child_conn,))
    p.start()
    return p, (parent_conn, child_conn,)

def worker(conn):
    """Process that sleeps and listens for messages"""
    print("Worker started.")

    # Sleep for 10 seconds
    time.sleep(.2)

    running = 1
    # Check if there's a message in the pipe
    while running:
        print('Waiting for input.')
        msg = conn.recv()
        if msg.lower() == 'stop':
            running = 0
            continue
        print(f"Worker received: {msg}")
        async_run(msg)
        print('Ran async worker')
        # running = 0
    conn.close()
    return

if __name__ == '__main__':
    main()