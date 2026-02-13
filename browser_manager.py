"""
Browser Manager with Pool Support
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Advanced browser management with connection pooling, retry logic, and health monitoring
"""

import time
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue, Empty, Full
from contextlib import contextmanager
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, NoSuchElementException, 
                                      WebDriverException, StaleElementReferenceException)

import config
import logger_system

logger = logger_system.get_logger(__name__)


@dataclass
class BrowserConfig:
    """Browser configuration"""
    headless: bool = True
    window_width: int = 1920
    window_height: int = 1080
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    binary_location: Optional[str] = None
    driver_path: Optional[str] = None
    download_directory: str = "downloads"
    proxy_enabled: bool = False
    proxy_address: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    page_load_timeout: int = 60
    script_timeout: int = 30
    implicit_wait: int = 10
    pool_size: int = 3
    max_retries: int = 3
    retry_delay: int = 5
    enable_logging: bool = True


@dataclass
class BrowserStats:
    """Browser statistics"""
    total_browsers: int = 0
    active_browsers: int = 0
    idle_browsers: int = 0
    total_page_loads: int = 0
    failed_page_loads: int = 0
    total_actions: int = 0
    failed_actions: int = 0
    avg_action_time: float = 0.0


@dataclass
class BrowserInstance:
    """Browser instance wrapper"""
    driver: webdriver.Chrome
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    is_healthy: bool = True
    process_id: str = ""


class BrowserPool:
    """
    Thread-safe browser pool for managing multiple browser instances
    """
    
    def __init__(self, pool_size: int = 3, config: Optional[BrowserConfig] = None):
        self.pool_size = pool_size
        self.config = config or BrowserConfig()
        self._pool: Queue[BrowserInstance] = Queue(maxsize=pool_size)
        self._lock = threading.RLock()
        self._stats = BrowserStats()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_running = False
        
        # Initialize browsers
        self._initialize_pool()
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        logger.info(f"Browser pool initialized: {pool_size} browsers")
    
    def _initialize_pool(self):
        """Initialize browser pool"""
        for i in range(self.pool_size):
            browser = self._create_browser()
            if browser:
                self._pool.put(browser)
                with self._lock:
                    self._stats.total_browsers += 1
        
        with self._lock:
            self._stats.idle_browsers = self.pool_size
    
    def _create_browser(self) -> Optional[BrowserInstance]:
        """Create a new browser instance"""
        try:
            chrome_options = Options()
            
            # Headless mode
            if self.config.headless:
                chrome_options.add_argument('--headless=new')
            
            # Security and sandbox
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-setuid-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            
            # Window size
            chrome_options.add_argument(f'--window-size={self.config.window_width},{self.config.window_height}')
            
            # User agent
            chrome_options.add_argument(f'--user-agent={self.config.user_agent}')
            
            # Download directory
            download_dir = Path(self.config.download_directory)
            download_dir.mkdir(parents=True, exist_ok=True)
            chrome_prefs = {
                'download.default_directory': str(download_dir.absolute()),
                'download.prompt_for_download': False,
                'download.directory_upgrade': True,
                'safebrowsing.enabled': True
            }
            chrome_options.add_experimental_option('prefs', chrome_prefs)
            
            # Proxy configuration
            if self.config.proxy_enabled and self.config.proxy_address:
                proxy_str = f"{self.config.proxy_address}:{self.config.proxy_port}"
                if self.config.proxy_username and self.config.proxy_password:
                    proxy_str = f"{self.config.proxy_username}:{self.config.proxy_password}@{proxy_str}"
                chrome_options.add_argument(f'--proxy-server=http://{proxy_str}')
            
            # Binary location
            if self.config.binary_location:
                chrome_options.binary_location = self.config.binary_location
            
            # Find Chromium binary
            chromium_paths = [
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser',
                '/usr/bin/google-chrome',
                '/usr/bin/chrome',
                '/Applications/Chromium.app/Contents/MacOS/Chromium',
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            ]
            
            if not self.config.binary_location:
                for chromium_path in chromium_paths:
                    if Path(chromium_path).exists():
                        chrome_options.binary_location = chromium_path
                        logger.debug(f"Found Chromium at: {chromium_path}")
                        break
            
            # Find ChromeDriver
            driver_path = self.config.driver_path
            if not driver_path:
                chromedriver_paths = [
                    '/usr/bin/chromedriver',
                    '/usr/local/bin/chromedriver',
                    '/opt/homebrew/bin/chromedriver'
                ]
                for driver_candidate in chromedriver_paths:
                    if Path(driver_candidate).exists():
                        driver_path = driver_candidate
                        logger.debug(f"Found ChromeDriver at: {driver_path}")
                        break
            
            # Create driver
            if driver_path:
                service = Service(executable_path=driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            
            # Set timeouts
            driver.set_page_load_timeout(self.config.page_load_timeout)
            driver.set_script_timeout(self.config.script_timeout)
            driver.implicitly_wait(self.config.implicit_wait)
            
            # Set window size
            driver.set_window_size(self.config.window_width, self.config.window_height)
            
            # Create browser instance
            browser = BrowserInstance(
                driver=driver,
                process_id=f"BROWSER-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            
            logger.info(f"Browser created: {browser.process_id}")
            return browser
        
        except Exception as e:
            logger.error(f"Failed to create browser: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        self._cleanup_running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_loop(self):
        """Cleanup loop for idle browsers"""
        while self._cleanup_running:
            try:
                time.sleep(300)  # Check every 5 minutes
                self._cleanup_idle_browsers()
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    def _cleanup_idle_browsers(self):
        """Clean up idle browsers that haven't been used recently"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            # This is a simplified cleanup - in production, you'd want more sophisticated logic
            # For now, we just log about idle browsers
            if self._stats.idle_browsers > 0:
                logger.debug(f"Found {self._stats.idle_browsers} idle browsers")
    
    @contextmanager
    def get_browser(self, timeout: float = 60.0, retry_on_failure: bool = True):
        """
        Get a browser from the pool (context manager)
        
        Args:
            timeout: Maximum time to wait for a browser
            retry_on_failure: Whether to retry on browser failure
            
        Yields:
            BrowserInstance: Browser instance
        """
        browser = None
        start_time = time.time()
        retries = 0
        
        try:
            while retries < self.config.max_retries:
                try:
                    # Try to get browser with timeout
                    browser = self._pool.get(timeout=min(timeout, 30.0))
                    
                    with self._lock:
                        self._stats.idle_browsers -= 1
                        self._stats.active_browsers += 1
                    
                    # Verify browser is healthy
                    try:
                        browser.driver.execute_script("return navigator.userAgent;")
                        break  # Browser is healthy
                    except Exception:
                        # Browser is not healthy, create new one
                        logger.warning(f"Browser {browser.process_id} is unhealthy, recreating...")
                        try:
                            browser.driver.quit()
                        except:
                            pass
                        
                        browser = self._create_browser()
                        if not browser:
                            retries += 1
                            time.sleep(self.config.retry_delay)
                            continue
                
                except Empty:
                    logger.warning(f"No browser available, retrying... ({retries + 1}/{self.config.max_retries})")
                    retries += 1
                    time.sleep(self.config.retry_delay)
            
            if not browser:
                raise TimeoutError(f"Could not get healthy browser after {retries} retries")
            
            # Update browser stats
            browser.last_used = datetime.now()
            browser.usage_count += 1
            
            yield browser
        
        except Exception as e:
            logger.error(f"Browser pool error: {e}")
            if retry_on_failure:
                raise
        finally:
            if browser:
                # Return browser to pool
                try:
                    self._pool.put_nowait(browser)
                    with self._lock:
                        self._stats.active_browsers -= 1
                        self._stats.idle_browsers += 1
                except Full:
                    # Pool is full, close the browser
                    try:
                        browser.driver.quit()
                    except:
                        pass
                    with self._lock:
                        self._stats.active_browsers -= 1
                        self._stats.total_browsers -= 1
    
    def close_all(self):
        """Close all browsers in the pool"""
        self._cleanup_running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        
        with self._lock:
            while not self._pool.empty():
                try:
                    browser = self._pool.get_nowait()
                    try:
                        browser.driver.quit()
                    except:
                        pass
                except Empty:
                    break
            
            self._stats.total_browsers = 0
            self._stats.active_browsers = 0
            self._stats.idle_browsers = 0
        
        logger.info("All browsers closed")
    
    def get_stats(self) -> BrowserStats:
        """Get browser pool statistics"""
        with self._lock:
            return self._stats


class BrowserManager:
    """
    High-level browser manager with common operations
    """
    
    def __init__(self, pool_size: int = 3, config: Optional[BrowserConfig] = None):
        self.pool = BrowserPool(pool_size, config)
        self.config = config or BrowserConfig()
    
    @contextmanager
    def browser(self, timeout: float = 60.0):
        """Context manager for getting a browser"""
        with self.pool.get_browser(timeout=timeout) as browser:
            yield browser
    
    def navigate_to(self, browser: BrowserInstance, url: str, 
                   wait_for_load: bool = True, wait_time: int = 5) -> bool:
        """Navigate to a URL"""
        try:
            start_time = time.time()
            
            if wait_for_load:
                browser.driver.get(url)
            else:
                browser.driver.execute_script(f"window.location.href = '{url}'")
            
            if wait_time > 0:
                time.sleep(wait_time)
            
            # Update stats
            load_time = time.time() - start_time
            with self.pool._lock:
                self.pool._stats.total_page_loads += 1
            
            logger.info(f"Navigated to {url} (took {load_time:.2f}s)")
            return True
        
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            with self.pool._lock:
                self.pool._stats.failed_page_loads += 1
            return False
    
    def find_element(self, browser: BrowserInstance, selector: str, 
                    by: By = By.CSS_SELECTOR, timeout: int = 10) -> Optional[Any]:
        """Find an element with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                wait = WebDriverWait(browser.driver, timeout)
                element = wait.until(EC.presence_of_element_located((by, selector)))
                return element
            except TimeoutException:
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                    continue
                return None
            except Exception as e:
                logger.warning(f"Element find error: {e}")
                time.sleep(self.config.retry_delay)
        
        return None
    
    def find_elements(self, browser: BrowserInstance, selector: str,
                     by: By = By.CSS_SELECTOR, timeout: int = 10) -> List[Any]:
        """Find multiple elements"""
        try:
            wait = WebDriverWait(browser.driver, timeout)
            elements = wait.until(EC.presence_of_all_elements_located((by, selector)))
            return elements
        except Exception as e:
            logger.warning(f"Elements find error: {e}")
            return []
    
    def click_element(self, browser: BrowserInstance, element: Any, 
                     wait_after: float = 1.0) -> bool:
        """Click an element with retry logic"""
        try:
            start_time = time.time()
            
            # Scroll element into view
            browser.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(0.5)
            
            # Click element
            element.click()
            
            if wait_after > 0:
                time.sleep(wait_after)
            
            # Update stats
            action_time = time.time() - start_time
            with self.pool._lock:
                self.pool._stats.total_actions += 1
                self.pool._stats.avg_action_time = (
                    self.pool._stats.avg_action_time * (self.pool._stats.total_actions - 1) + action_time
                ) / self.pool._stats.total_actions
            
            return True
        
        except StaleElementReferenceException:
            logger.warning("Stale element reference, retrying...")
            return self.click_element(browser, element, wait_after)
        except Exception as e:
            logger.error(f"Click error: {e}")
            with self.pool._lock:
                self.pool._stats.failed_actions += 1
            return False
    
    def input_text(self, browser: BrowserInstance, element: Any, text: str,
                  clear: bool = True, wait_after: float = 0.5) -> bool:
        """Input text into an element"""
        try:
            start_time = time.time()
            
            # Clear existing text if requested
            if clear:
                element.clear()
                time.sleep(0.2)
            
            # Type text
            element.send_keys(text)
            
            if wait_after > 0:
                time.sleep(wait_after)
            
            # Update stats
            action_time = time.time() - start_time
            with self.pool._lock:
                self.pool._stats.total_actions += 1
                self.pool._stats.avg_action_time = (
                    self.pool._stats.avg_action_time * (self.pool._stats.total_actions - 1) + action_time
                ) / self.pool._stats.total_actions
            
            return True
        
        except Exception as e:
            logger.error(f"Input text error: {e}")
            with self.pool._lock:
                self.pool._stats.failed_actions += 1
            return False
    
    def execute_script(self, browser: BrowserInstance, script: str, *args) -> Any:
        """Execute JavaScript in browser"""
        try:
            return browser.driver.execute_script(script, *args)
        except Exception as e:
            logger.error(f"Script execution error: {e}")
            return None
    
    def get_cookies(self, browser: BrowserInstance) -> List[Dict[str, Any]]:
        """Get all cookies from browser"""
        try:
            return browser.driver.get_cookies()
        except Exception as e:
            logger.error(f"Get cookies error: {e}")
            return []
    
    def add_cookies(self, browser: BrowserInstance, cookies: str) -> bool:
        """Add cookies to browser"""
        try:
            cookie_array = cookies.split(';')
            for cookie in cookie_array:
                cookie = cookie.strip()
                if cookie:
                    equal_index = cookie.find('=')
                    if equal_index > 0:
                        name = cookie[:equal_index].strip()
                        value = cookie[equal_index + 1:].strip()
                        try:
                            browser.driver.add_cookie({
                                'name': name,
                                'value': value,
                                'domain': '.facebook.com',
                                'path': '/'
                            })
                        except Exception:
                            pass
            return True
        except Exception as e:
            logger.error(f"Add cookies error: {e}")
            return False
    
    def take_screenshot(self, browser: BrowserInstance, filename: str) -> bool:
        """Take a screenshot"""
        try:
            screenshot_dir = Path("screenshots")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = screenshot_dir / filename
            
            browser.driver.save_screenshot(str(screenshot_path))
            logger.info(f"Screenshot saved: {screenshot_path}")
            return True
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return False
    
    def get_page_source(self, browser: BrowserInstance) -> str:
        """Get page source"""
        try:
            return browser.driver.page_source
        except Exception as e:
            logger.error(f"Get page source error: {e}")
            return ""
    
    def wait_for_element(self, browser: BrowserInstance, selector: str,
                        by: By = By.CSS_SELECTOR, timeout: int = 30) -> bool:
        """Wait for element to be present and visible"""
        try:
            wait = WebDriverWait(browser.driver, timeout)
            wait.until(EC.visibility_of_element_located((by, selector)))
            return True
        except TimeoutException:
            return False
        except Exception as e:
            logger.error(f"Wait for element error: {e}")
            return False
    
    def scroll_to_bottom(self, browser: BrowserInstance):
        """Scroll to bottom of page"""
        try:
            browser.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Scroll to bottom error: {e}")
    
    def scroll_to_top(self, browser: BrowserInstance):
        """Scroll to top of page"""
        try:
            browser.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Scroll to top error: {e}")
    
    def refresh_page(self, browser: BrowserInstance, wait_time: int = 5):
        """Refresh the current page"""
        try:
            browser.driver.refresh()
            if wait_time > 0:
                time.sleep(wait_time)
        except Exception as e:
            logger.error(f"Refresh page error: {e}")
    
    def get_current_url(self, browser: BrowserInstance) -> str:
        """Get current URL"""
        try:
            return browser.driver.current_url
        except Exception as e:
            logger.error(f"Get current URL error: {e}")
            return ""
    
    def get_page_title(self, browser: BrowserInstance) -> str:
        """Get page title"""
        try:
            return browser.driver.title
        except Exception as e:
            logger.error(f"Get page title error: {e}")
            return ""
    
    def is_element_present(self, browser: BrowserInstance, selector: str,
                          by: By = By.CSS_SELECTOR) -> bool:
        """Check if element is present"""
        try:
            browser.driver.find_element(by, selector)
            return True
        except NoSuchElementException:
            return False
        except Exception as e:
            logger.warning(f"Is element present error: {e}")
            return False
    
    def get_element_text(self, browser: BrowserInstance, element: Any) -> str:
        """Get text from element"""
        try:
            return element.text.strip()
        except Exception as e:
            logger.error(f"Get element text error: {e}")
            return ""
    
    def get_element_attribute(self, browser: BrowserInstance, element: Any, attribute: str) -> str:
        """Get attribute value from element"""
        try:
            return element.get_attribute(attribute) or ""
        except Exception as e:
            logger.error(f"Get element attribute error: {e}")
            return ""
    
    def close(self):
        """Close browser manager"""
        self.pool.close_all()
        logger.info("BrowserManager closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get browser manager statistics"""
        pool_stats = self.pool.get_stats()
        
        return {
            'pool': {
                'total_browsers': pool_stats.total_browsers,
                'active_browsers': pool_stats.active_browsers,
                'idle_browsers': pool_stats.idle_browsers
            },
            'performance': {
                'total_page_loads': pool_stats.total_page_loads,
                'failed_page_loads': pool_stats.failed_page_loads,
                'total_actions': pool_stats.total_actions,
                'failed_actions': pool_stats.failed_actions,
                'avg_action_time': pool_stats.avg_action_time
            }
        }


# Global browser manager instance
browser_manager = None


def get_browser_manager(pool_size: int = 3) -> BrowserManager:
    """Get global browser manager instance"""
    global browser_manager
    if browser_manager is None:
        browser_manager = BrowserManager(pool_size=pool_size)
    return browser_manager


if __name__ == "__main__":
    # Test browser manager
    print("Testing Browser Manager...")
    
    manager = get_browser_manager(pool_size=1)
    
    # Test browser operations
    with manager.browser() as browser:
        success = manager.navigate_to(browser, "https://www.google.com")
        print(f"Navigation success: {success}")
        
        url = manager.get_current_url(browser)
        print(f"Current URL: {url}")
        
        title = manager.get_page_title(browser)
        print(f"Page title: {title}")
    
    # Get stats
    stats = manager.get_stats()
    print(f"Browser stats: {stats}")
    
    # Close manager
    manager.close()