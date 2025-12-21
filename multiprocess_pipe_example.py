from multiprocessing import Process, Pipe
import time

def worker(conn):
    """Process that sleeps and listens for messages"""
    print("Worker started, sleeping...")
    
    # Sleep for 10 seconds
    time.sleep(10)
    
    print("Worker awake, waiting for messages...")
    # Wait for messages in a loop
    while True:
        msg = conn.recv()  # Blocks until message received
        print(f"Worker received: {msg}")
        
        if msg == "STOP":
            print("Worker stopping...")
            break
    
    conn.close()

if __name__ == '__main__':
    # Create a pipe (returns two connection objects)
    parent_conn, child_conn = Pipe()
    
    # Start the process
    p = Process(target=worker, args=(child_conn,))
    p.start()
    
    # Send messages through the pipe
    time.sleep(1)  # Wait a bit before sending
    parent_conn.send("Hello from main process!")
    print("Message sent to worker")
    
    time.sleep(2)
    parent_conn.send("Another message!")
    print("Second message sent")
    
    time.sleep(1)
    parent_conn.send("STOP")
    print("Stop signal sent")
    
    # Wait for process to complete
    p.join()
    print("Worker finished")
