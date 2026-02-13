"""
Multi-Worker Automation Engine
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Advanced automation engine with multiple workers, scheduling, and error recovery
"""

import time
import threading
import queue
import uuid
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

import config
import logger_system
import database_enhanced as db
import browser_manager

logger = logger_system.get_logger(__name__)


class WorkerStatus(Enum):
    """Worker status enumeration"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"
    RESTARTING = "restarting"


@dataclass
class Task:
    """Automation task"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int = 0
    chat_id: str = ""
    name_prefix: str = ""
    delay: int = 30
    cookies: str = ""
    messages: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    priority: int = 5  # 1-10, higher is more important
    max_retries: int = 3
    retry_count: int = 0
    status: str = "pending"


@dataclass
class Worker:
    """Automation worker"""
    worker_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: WorkerStatus = WorkerStatus.IDLE
    current_task: Optional[Task] = None
    total_tasks_completed: int = 0
    total_messages_sent: int = 0
    total_errors: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    thread: Optional[threading.Thread] = None
    stop_event: threading.Event = field(default_factory=threading.Event)


@dataclass
class AutomationStats:
    """Automation statistics"""
    total_workers: int = 0
    active_workers: int = 0
    idle_workers: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_messages_sent: int = 0
    uptime: float = 0.0
    avg_task_time: float = 0.0


class AutomationEngine:
    """
    Multi-worker automation engine with scheduling and error recovery
    """
    
    def __init__(self, max_workers: int = 5, config: Optional[config.AutomationConfig] = None):
        self.max_workers = max_workers
        self.config = config or config.AutomationConfig()
        
        # Workers
        self.workers: Dict[str, Worker] = {}
        self.worker_lock = threading.RLock()
        
        # Task queues
        self.task_queue = queue.PriorityQueue()
        self.running_tasks: Dict[str, Task] = {}
        
        # Browser manager
        self.browser_mgr = browser_manager.get_browser_manager(pool_size=max_workers)
        
        # Database
        self.db = db.get_database()
        
        # Control flags
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Statistics
        self.stats = AutomationStats()
        self.stats_lock = threading.RLock()
        
        # Event handlers
        self.on_task_completed: Optional[Callable] = None
        self.on_task_failed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        logger.info(f"AutomationEngine initialized: {max_workers} workers")
    
    def start(self):
        """Start the automation engine"""
        if self.running:
            logger.warning("Automation engine is already running")
            return
        
        self.running = True
        
        # Initialize workers
        self._initialize_workers()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Automation engine started")
    
    def stop(self):
        """Stop the automation engine"""
        if not self.running:
            return
        
        self.running = False
        
        # Stop all workers
        self._stop_all_workers()
        
        # Wait for threads
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        
        logger.info("Automation engine stopped")
    
    def _initialize_workers(self):
        """Initialize worker threads"""
        with self.worker_lock:
            for i in range(self.max_workers):
                worker = Worker(
                    worker_id=f"WORKER-{i+1}",
                    stop_event=threading.Event()
                )
                
                worker.thread = threading.Thread(
                    target=self._worker_loop,
                    args=(worker,),
                    daemon=True
                )
                worker.thread.start()
                
                self.workers[worker.worker_id] = worker
                
                with self.stats_lock:
                    self.stats.total_workers += 1
                    self.stats.idle_workers += 1
        
        logger.info(f"Initialized {self.max_workers} workers")
    
    def _stop_all_workers(self):
        """Stop all worker threads"""
        with self.worker_lock:
            for worker in self.workers.values():
                worker.stop_event.set()
                worker.status = WorkerStatus.STOPPED
        
        # Wait for workers to stop
        for worker in self.workers.values():
            if worker.thread:
                worker.thread.join(timeout=5)
        
        logger.info("All workers stopped")
    
    def _scheduler_loop(self):
        """Scheduler loop to assign tasks to workers"""
        while self.running:
            try:
                # Get next task from queue
                try:
                    priority, task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Find idle worker
                idle_worker = self._find_idle_worker()
                if not idle_worker:
                    # Put task back in queue
                    self.task_queue.put((priority, task))
                    time.sleep(1)
                    continue
                
                # Assign task to worker
                with self.worker_lock:
                    idle_worker.current_task = task
                    idle_worker.status = WorkerStatus.BUSY
                    idle_worker.last_activity = datetime.now()
                
                with self.stats_lock:
                    self.stats.active_workers += 1
                    self.stats.idle_workers -= 1
                
                logger.info(f"Task {task.task_id} assigned to {idle_worker.worker_id}")
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(5)
    
    def _worker_loop(self, worker: Worker):
        """Worker loop to process tasks"""
        while self.running and not worker.stop_event.is_set():
            try:
                if worker.current_task is None:
                    time.sleep(0.5)
                    continue
                
                task = worker.current_task
                
                # Execute task
                start_time = time.time()
                success = self._execute_task(worker, task)
                task_time = time.time() - start_time
                
                # Update worker stats
                with self.worker_lock:
                    worker.total_tasks_completed += 1
                    worker.last_activity = datetime.now()
                    if success:
                        worker.total_messages_sent += len(task.messages)
                    else:
                        worker.total_errors += 1
                    worker.current_task = None
                    worker.status = WorkerStatus.IDLE
                
                with self.stats_lock:
                    self.stats.completed_tasks += 1
                    self.stats.total_messages_sent += len(task.messages)
                    self.stats.avg_task_time = (
                        self.stats.avg_task_time * (self.stats.completed_tasks - 1) + task_time
                    ) / self.stats.completed_tasks
                    self.stats.active_workers -= 1
                    self.stats.idle_workers += 1
                
                # Log to database
                self.db.log_automation_event(
                    task.user_id,
                    worker.worker_id,
                    "INFO" if success else "ERROR",
                    f"Task {task.task_id} {'completed' if success else 'failed'} in {task_time:.2f}s"
                )
                
                # Remove from running tasks
                if task.task_id in self.running_tasks:
                    del self.running_tasks[task.task_id]
                
                # Call handlers
                if success:
                    if self.on_task_completed:
                        self.on_task_completed(task, worker)
                else:
                    if self.on_task_failed:
                        self.on_task_failed(task, worker)
                
                # Handle retries
                if not success and task.retry_count < task.max_retries:
                    task.retry_count += 1
                    logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count}/{task.max_retries})")
                    time.sleep(self.config.auto_restart_delay)
                    self.add_task(task)
                else:
                    with self.stats_lock:
                        if not success:
                            self.stats.failed_tasks += 1
                
            except Exception as e:
                logger.error(f"Worker {worker.worker_id} loop error: {e}")
                
                # Update worker status
                with self.worker_lock:
                    worker.status = WorkerStatus.ERROR
                    worker.total_errors += 1
                
                # Call error handler
                if self.on_error:
                    self.on_error(worker, e)
                
                # Attempt recovery
                if self.config.auto_restart_enabled:
                    self._restart_worker(worker)
                else:
                    time.sleep(5)
    
    def _execute_task(self, worker: Worker, task: Task) -> bool:
        """Execute a task"""
        try:
            logger.info(f"Executing task {task.task_id} on {worker.worker_id}")
            
            # Get browser from pool
            with self.browser_mgr.browser() as browser:
                # Navigate to Facebook
                logger.info(f"{worker.worker_id}: Navigating to Facebook...")
                self.browser_mgr.navigate_to(browser, "https://www.facebook.com/")
                time.sleep(8)
                
                # Add cookies
                if task.cookies and task.cookies.strip():
                    logger.info(f"{worker.worker_id}: Adding cookies...")
                    self.browser_mgr.add_cookies(browser, task.cookies)
                    time.sleep(2)
                
                # Navigate to chat
                if task.chat_id:
                    logger.info(f"{worker.worker_id}: Opening conversation {task.chat_id}...")
                    # Try e2ee URL first
                    self.browser_mgr.navigate_to(browser, f"https://www.facebook.com/messages/e2ee/t/{task.chat_id}")
                    time.sleep(5)
                    
                    # Fallback to normal messages URL
                    if "/e2ee/" not in self.browser_mgr.get_current_url(browser):
                        self.browser_mgr.navigate_to(browser, f"https://www.facebook.com/messages/t/{task.chat_id}")
                else:
                    logger.info(f"{worker.worker_id}: Opening messages...")
                    self.browser_mgr.navigate_to(browser, "https://www.facebook.com/messages")
                
                time.sleep(15)
                
                # Find message input
                message_input = self._find_message_input(browser, worker.worker_id)
                if not message_input:
                    logger.error(f"{worker.worker_id}: Message input not found")
                    return False
                
                # Send messages
                message_index = 0
                success_count = 0
                
                while not worker.stop_event.is_set() and message_index < len(task.messages):
                    try:
                        message = task.messages[message_index]
                        
                        # Add prefix if specified
                        if task.name_prefix:
                            full_message = f"{task.name_prefix} {message}"
                        else:
                            full_message = message
                        
                        # Send message
                        if self._send_message(browser, message_input, full_message, worker.worker_id):
                            success_count += 1
                            logger.info(f"{worker.worker_id}: Sent message {message_index + 1}/{len(task.messages)}")
                            
                            # Log to database
                            self.db.log_message(task.user_id, task.chat_id, full_message, True)
                        else:
                            logger.error(f"{worker.worker_id}: Failed to send message {message_index + 1}")
                            self.db.log_message(task.user_id, task.chat_id, full_message, False)
                        
                        message_index += 1
                        
                        # Wait before next message
                        if message_index < len(task.messages):
                            time.sleep(task.delay)
                    
                    except Exception as e:
                        logger.error(f"{worker.worker_id}: Message send error: {e}")
                        time.sleep(5)
                
                logger.info(f"{worker.worker_id}: Task completed. Sent {success_count}/{len(task.messages)} messages")
                return success_count > 0
        
        except Exception as e:
            logger.error(f"{worker.worker_id}: Task execution error: {e}")
            return False
    
    def _find_message_input(self, browser: browser_manager.BrowserInstance, worker_id: str):
        """Find message input element"""
        logger.info(f"{worker_id}: Finding message input...")
        time.sleep(10)
        
        # Scroll
        try:
            self.browser_mgr.scroll_to_bottom(browser)
            time.sleep(2)
            self.browser_mgr.scroll_to_top(browser)
            time.sleep(2)
        except Exception:
            pass
        
        # Get page info
        try:
            page_title = self.browser_mgr.get_page_title(browser)
            page_url = self.browser_mgr.get_current_url(browser)
            logger.info(f"{worker_id}: Page - {page_title} ({page_url})")
        except Exception:
            pass
        
        # Try selectors
        selectors = [
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"][data-lexical-editor="true"]',
            'div[aria-label*="message" i][contenteditable="true"]',
            'div[contenteditable="true"][spellcheck="true"]',
            '[role="textbox"][contenteditable="true"]',
            'textarea[placeholder*="message" i]',
            'div[aria-placeholder*="message" i]',
        ]
        
        for idx, selector in enumerate(selectors):
            try:
                elements = self.browser_mgr.find_elements(browser.browser, selector)
                logger.info(f"{worker_id}: Selector {idx+1} found {len(elements)} elements")
                
                for element in elements:
                    try:
                        # Check if editable
                        is_editable = self.browser_mgr.execute_script(
                            browser.browser,
                            "return arguments[0].contentEditable === 'true' || arguments[0].tagName === 'TEXTAREA';",
                            element
                        )
                        
                        if is_editable:
                            logger.info(f"{worker_id}: Found editable element")
                            return element
                    
                    except Exception:
                        continue
            
            except Exception:
                continue
        
        logger.error(f"{worker_id}: Message input not found")
        return None
    
    def _send_message(self, browser: browser_manager.BrowserInstance, 
                     message_input: Any, message: str, worker_id: str) -> bool:
        """Send a message"""
        try:
            # Type message
            self.browser_mgr.execute_script(
                browser.browser,
                """
                const element = arguments[0];
                const message = arguments[1];
                element.scrollIntoView({behavior: 'smooth', block: 'center'});
                element.focus();
                element.click();
                if (element.tagName === 'DIV') {
                    element.textContent = message;
                    element.innerHTML = message;
                } else {
                    element.value = message;
                }
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                """,
                message_input,
                message
            )
            time.sleep(1)
            
            # Try to click send button
            sent = self.browser_mgr.execute_script(
                browser.browser,
                """
                const buttons = document.querySelectorAll('[aria-label*="Send" i]:not([aria-label*="like" i]), [data-testid="send-button"]');
                for (let btn of buttons) {
                    if (btn.offsetParent !== null) {
                        btn.click();
                        return 'clicked';
                    }
                }
                return 'not_found';
                """
            )
            
            if sent == 'clicked':
                logger.info(f"{worker_id}: Sent via button")
                time.sleep(1)
                return True
            
            # Try Enter key
            self.browser_mgr.execute_script(
                browser.browser,
                """
                const element = arguments[0];
                element.focus();
                const events = [
                    new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }),
                    new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }),
                    new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true })
                ];
                events.forEach(event => element.dispatchEvent(event));
                """,
                message_input
            )
            logger.info(f"{worker_id}: Sent via Enter")
            time.sleep(1)
            return True
        
        except Exception as e:
            logger.error(f"{worker_id}: Send error: {e}")
            return False
    
    def _monitor_loop(self):
        """Monitor loop for health checks and statistics"""
        while self.running:
            try:
                # Record uptime
                with self.stats_lock:
                    self.stats.uptime = time.time() - min(
                        (w.start_time for w in self.workers.values() if w.start_time),
                        default=datetime.now()
                    ).timestamp()
                
                # Record metrics to database
                self.db.record_metric("active_workers", self.stats.active_workers)
                self.db.record_metric("total_messages_sent", self.stats.total_messages_sent)
                self.db.record_metric("avg_task_time", self.stats.avg_task_time)
                
                # Check worker health
                self._check_worker_health()
                
                # Sleep until next check
                time.sleep(self.config.health_check_interval)
            
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(30)
    
    def _check_worker_health(self):
        """Check health of all workers"""
        with self.worker_lock:
            for worker in self.workers.values():
                # Check if worker is stuck
                if worker.status == WorkerStatus.BUSY:
                    idle_time = (datetime.now() - worker.last_activity).total_seconds()
                    if idle_time > self.config.worker_timeout:
                        logger.warning(f"Worker {worker.worker_id} appears stuck (idle for {idle_time}s)")
                        if self.config.auto_restart_enabled:
                            self._restart_worker(worker)
    
    def _restart_worker(self, worker: Worker):
        """Restart a worker"""
        logger.info(f"Restarting worker {worker.worker_id}...")
        
        with self.worker_lock:
            worker.status = WorkerStatus.RESTARTING
        
        # Stop current task
        if worker.current_task:
            # Put task back in queue for retry
            self.add_task(worker.current_task)
            worker.current_task = None
        
        # Wait a bit
        time.sleep(self.config.auto_restart_delay)
        
        # Reset worker state
        with self.worker_lock:
            worker.status = WorkerStatus.IDLE
            worker.last_activity = datetime.now()
            if worker.status == WorkerStatus.ERROR:
                worker.total_errors = 0
        
        logger.info(f"Worker {worker.worker_id} restarted")
    
    def _find_idle_worker(self) -> Optional[Worker]:
        """Find an idle worker"""
        with self.worker_lock:
            for worker in self.workers.values():
                if worker.status == WorkerStatus.IDLE:
                    return worker
        return None
    
    def add_task(self, task: Task):
        """Add a task to the queue"""
        # Use negative priority for PriorityQueue (higher priority = smaller number)
        self.task_queue.put((-task.priority, task))
        
        with self.stats_lock:
            self.stats.total_tasks += 1
        
        logger.info(f"Task {task.task_id} added to queue (priority: {task.priority})")
    
    def add_task_from_config(self, user_id: int, user_config: Dict[str, Any]) -> bool:
        """Add task from user configuration"""
        try:
            messages = [msg.strip() for msg in user_config['messages'].split('\n') if msg.strip()]
            
            if not messages:
                messages = ["Hello!"]
            
            task = Task(
                user_id=user_id,
                chat_id=user_config.get('chat_id', ''),
                name_prefix=user_config.get('name_prefix', ''),
                delay=user_config.get('delay', 30),
                cookies=user_config.get('cookies', ''),
                messages=messages,
                priority=5
            )
            
            self.add_task(task)
            return True
        
        except Exception as e:
            logger.error(f"Failed to add task from config: {e}")
            return False
    
    def get_stats(self) -> AutomationStats:
        """Get automation statistics"""
        with self.stats_lock:
            return self.stats
    
    def get_worker_stats(self) -> List[Dict[str, Any]]:
        """Get individual worker statistics"""
        with self.worker_lock:
            return [
                {
                    'worker_id': w.worker_id,
                    'status': w.status.value,
                    'total_tasks_completed': w.total_tasks_completed,
                    'total_messages_sent': w.total_messages_sent,
                    'total_errors': w.total_errors,
                    'uptime': (datetime.now() - w.start_time).total_seconds(),
                    'current_task': w.current_task.task_id if w.current_task else None
                }
                for w in self.workers.values()
            ]
    
    def close(self):
        """Close automation engine"""
        self.stop()
        self.browser_mgr.close()
        logger.info("AutomationEngine closed")


# Global automation engine instance
automation_engine = None


def get_automation_engine(max_workers: int = 5) -> AutomationEngine:
    """Get global automation engine instance"""
    global automation_engine
    if automation_engine is None:
        automation_engine = AutomationEngine(max_workers=max_workers)
    return automation_engine


if __name__ == "__main__":
    # Test automation engine
    print("Testing Automation Engine...")
    
    engine = get_automation_engine(max_workers=2)
    engine.start()
    
    # Add test task
    task = Task(
        user_id=1,
        chat_id="",
        messages=["Test message 1", "Test message 2"],
        delay=10
    )
    engine.add_task(task)
    
    # Wait a bit
    time.sleep(5)
    
    # Get stats
    stats = engine.get_stats()
    print(f"Automation stats: {stats}")
    
    worker_stats = engine.get_worker_stats()
    print(f"Worker stats: {worker_stats}")
    
    # Stop engine
    engine.stop()
    engine.close()