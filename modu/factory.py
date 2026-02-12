
from queue import Queue
from threading import Event, Thread
from typing import Callable

class Factory:
    def __init__(self, work: Callable, max_workers: int = 16, **kwargs):
        self.work = work
        self.max_workers = max_workers
        self.timeout = kwargs.get('timeout')
        self.task_queue = Queue()
        self.result_queue = Queue()
        self.start_event = Event()
        self.stop_event = Event()
        self.threads = []
    
    def worker(
            self,
            work: Callable,
            tasks: Queue,
            results: Queue | None = None,
            start_event: Event | None = None,
            stop_event: Event | None = None,
            timeout: int | None = None
        ):
        """
        ***work***
            a `func` for deal with the `tasks`

        ***tasks***
            `Queue` whose item is for `work(*args)`

        ***results***
            this is a `Queue`. `results.put(work(*args))`
            
        ***stop_event***
            a `Event` flag to break this worker

        ***timeout***
            how long will break after `tasks.empty()`. default `None` no wait.
        
        """
        task_ok = 0
        task_error = 0
        while True:
            if stop_event and stop_event.is_set():
                break
            if start_event:
                start_event.wait(timeout)
            if tasks.empty():
                if start_event:
                    start_event.clear()
                    continue
                else:
                    break
            task = tasks.get()
            try:
                result = work(*task)
            except Exception as e:
                print("worker do work error:", e)
                task_error += 1
                continue
            if type(result) == list:
                for item in result:
                    results.put(item)
            elif result is None:
                pass
            else:
                results.put(result)
            task_ok += 1
        return {
            "ok": task_ok,
            "error": task_error
            }
    
    def add_tasks(self, *tasks):
        """
        ***task***
            the `args` for `work(*args)`
        """
        for task in tasks:
            self.task_queue.put(task)

    def clear_tasks(self, *tasks):
        self.start_event.clear()
        if len(tasks) == 0:
            while not self.task_queue.empty():
                task = self.task_queue.get()
            return self.task_queue.qsize()
        else:
            for task in tasks:
                while not self.task_queue.empty():
                    t = self.task_queue.get()
                    if task == t:
                        continue
                    self.task_queue.put(t)
            self.start_event.set()
            return self.task_queue.qsize()
        
    def start(self):
        if self.task_queue.empty():
            return 0
        self.stop_event.clear()
        for thread in self.threads:
            if thread.is_alive():
                continue
            else:
                self.threads.remove(thread)
        for _ in range(len(self.threads), self.max_workers):
            thread = Thread(target=self.worker, args=(self.work, self.task_queue, self.result_queue, self.start_event, self.stop_event), daemon=True)
            thread.start()
            self.threads.append(thread)
        self.start_event.set()

    def pause(self):
        self.start_event.clear()

    def resume(self):
        self.start_event.set()

    def stop(self):
        self.stop_event.set()



