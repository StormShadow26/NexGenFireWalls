#!/usr/bin/env python3

"""
Realistic Traffic Generator for Step1 Firewall Testing

This script generates diverse, realistic network traffic patterns including:
- External HTTP/HTTPS requests to real websites
- DNS queries to different servers
- Various protocols and port combinations
- Different packet sizes and timing patterns
- Both legitimate and suspicious traffic patterns
"""

import socket
import subprocess
import threading
import time
import random
import requests
import dns.resolver
import sys
from urllib3.exceptions import InsecureRequestWarning
import warnings

# Suppress SSL warnings for testing
warnings.simplefilter('ignore', InsecureRequestWarning)

class RealisticTrafficGenerator:
    def __init__(self):
        self.running = False
        self.threads = []
        
        # Real external websites for HTTP/HTTPS traffic
        self.websites = [
            'http://httpbin.org',
            'https://httpbin.org/ip',
            'https://api.github.com',
            'https://jsonplaceholder.typicode.com/posts/1',
            'http://example.com',
            'https://www.google.com',
            'https://stackoverflow.com',
            'https://www.wikipedia.org',
            'https://www.reddit.com',
            'https://news.ycombinator.com'
        ]
        
        # Real DNS servers
        self.dns_servers = [
            '8.8.8.8',      # Google
            '1.1.1.1',      # Cloudflare
            '9.9.9.9',      # Quad9
            '208.67.222.222',  # OpenDNS
            '8.8.4.4',      # Google Secondary
        ]
        
        # Domains to resolve
        self.domains = [
            'google.com', 'github.com', 'stackoverflow.com', 'reddit.com',
            'wikipedia.org', 'youtube.com', 'twitter.com', 'facebook.com',
            'amazon.com', 'microsoft.com', 'apple.com', 'netflix.com',
            'cloudflare.com', 'debian.org', 'ubuntu.com', 'python.org'
        ]
        
        # External IPs for various protocols
        self.external_ips = [
            '8.8.8.8', '1.1.1.1', '9.9.9.9', '208.67.222.222',
            '74.125.224.72',    # Google
            '151.101.193.140',  # Reddit
            '140.82.112.4',     # GitHub
            '104.16.132.229',   # Cloudflare
            '23.185.0.2',       # Stack Overflow
            '54.230.47.67'      # Amazon CloudFront
        ]
        
        # Common ports for different services
        self.service_ports = {
            'web': [80, 8080, 8000, 3000],
            'secure_web': [443, 8443],
            'dns': [53],
            'mail': [25, 587, 993, 995],
            'ssh': [22, 2222],
            'ftp': [21, 22],
            'database': [3306, 5432, 27017, 1433],
            'custom': [8888, 9000, 9090, 7000, 6379]
        }

    def log_info(self, message):
        print(f"🌐 {message}")

    def generate_http_traffic(self, duration=30):
        """Generate realistic HTTP/HTTPS traffic"""
        self.log_info("Starting HTTP/HTTPS traffic generation...")
        
        end_time = time.time() + duration
        session = requests.Session()
        session.verify = False  # For testing purposes
        
        while time.time() < end_time and self.running:
            try:
                url = random.choice(self.websites)
                
                # Random delays between requests (realistic browsing)
                delay = random.uniform(0.5, 3.0)
                time.sleep(delay)
                
                # Different request types
                if random.random() < 0.8:  # GET requests (80%)
                    response = session.get(url, timeout=5)
                elif random.random() < 0.9:  # POST requests (10%)
                    data = {'test': 'data', 'timestamp': int(time.time())}
                    response = session.post(url + '/post', json=data, timeout=5)
                else:  # HEAD requests (10%)
                    response = session.head(url, timeout=5)
                
                self.log_info(f"HTTP {response.status_code}: {url}")
                
            except Exception as e:
                # Expected for many URLs, continue generating traffic
                pass
    
    def generate_dns_traffic(self, duration=30):
        """Generate realistic DNS queries"""
        self.log_info("Starting DNS traffic generation...")
        
        end_time = time.time() + duration
        
        while time.time() < end_time and self.running:
            try:
                domain = random.choice(self.domains)
                dns_server = random.choice(self.dns_servers)
                
                # Configure resolver
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [dns_server]
                resolver.timeout = 2
                resolver.lifetime = 3
                
                # Different query types
                query_types = ['A', 'AAAA', 'MX', 'NS', 'TXT']
                query_type = random.choice(query_types)
                
                result = resolver.resolve(domain, query_type)
                self.log_info(f"DNS {query_type}: {domain} -> {dns_server}")
                
                # Realistic DNS query timing
                time.sleep(random.uniform(0.1, 1.0))
                
            except Exception as e:
                # DNS failures are normal, continue
                time.sleep(0.5)
    
    def generate_tcp_connections(self, duration=30):
        """Generate various TCP connections to external services"""
        self.log_info("Starting TCP connection attempts...")
        
        end_time = time.time() + duration
        
        while time.time() < end_time and self.running:
            try:
                target_ip = random.choice(self.external_ips)
                service_type = random.choice(list(self.service_ports.keys()))
                port = random.choice(self.service_ports[service_type])
                
                # Create socket and attempt connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                
                try:
                    result = sock.connect_ex((target_ip, port))
                    if result == 0:
                        self.log_info(f"TCP Connected: {target_ip}:{port} ({service_type})")
                        # Send some data for realistic traffic
                        if service_type == 'web':
                            sock.send(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
                        time.sleep(0.1)
                    else:
                        self.log_info(f"TCP Attempt: {target_ip}:{port} ({service_type})")
                except:
                    pass
                finally:
                    sock.close()
                
                # Realistic connection timing
                time.sleep(random.uniform(0.2, 2.0))
                
            except Exception as e:
                time.sleep(0.5)
    
    def generate_udp_traffic(self, duration=30):
        """Generate UDP traffic to various services"""
        self.log_info("Starting UDP traffic generation...")
        
        end_time = time.time() + duration
        
        while time.time() < end_time and self.running:
            try:
                target_ip = random.choice(self.external_ips)
                
                # Different UDP services
                udp_services = [
                    (53, b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06google\x03com\x00\x00\x01\x00\x01'),  # DNS query
                    (123, b'\x1b\x00\x00\x00\x00\x00\x00\x00'),  # NTP
                    (161, b'\x30\x26\x02\x01\x00\x04\x06public'),  # SNMP
                    (514, b'<14>Test syslog message'),  # Syslog
                ]
                
                port, data = random.choice(udp_services)
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1)
                
                try:
                    sock.sendto(data, (target_ip, port))
                    self.log_info(f"UDP Sent: {target_ip}:{port} ({len(data)} bytes)")
                    
                    # Try to receive response
                    try:
                        response, addr = sock.recvfrom(1024)
                        self.log_info(f"UDP Response: {addr[0]}:{addr[1]} ({len(response)} bytes)")
                    except socket.timeout:
                        pass
                        
                except Exception:
                    pass
                finally:
                    sock.close()
                
                time.sleep(random.uniform(0.1, 1.5))
                
            except Exception as e:
                time.sleep(0.5)
    
    def generate_ping_traffic(self, duration=30):
        """Generate ICMP ping traffic to external hosts"""
        self.log_info("Starting ICMP ping traffic...")
        
        end_time = time.time() + duration
        
        while time.time() < end_time and self.running:
            try:
                target_ip = random.choice(self.external_ips)
                
                # Different ping patterns
                ping_patterns = [
                    ['-c', '1'],                    # Single ping
                    ['-c', '3'],                    # Triple ping
                    ['-c', '1', '-s', '64'],       # Small packet
                    ['-c', '1', '-s', '1024'],     # Large packet
                    ['-c', '2', '-i', '0.5'],      # Fast interval
                ]
                
                pattern = random.choice(ping_patterns)
                cmd = ['ping'] + pattern + [target_ip]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, timeout=5)
                    if result.returncode == 0:
                        self.log_info(f"PING Success: {target_ip}")
                    else:
                        self.log_info(f"PING Failed: {target_ip}")
                except subprocess.TimeoutExpired:
                    self.log_info(f"PING Timeout: {target_ip}")
                
                time.sleep(random.uniform(1.0, 3.0))
                
            except Exception as e:
                time.sleep(1.0)
    
    def generate_suspicious_traffic(self, duration=30):
        """Generate suspicious traffic patterns for testing firewall detection"""
        self.log_info("Starting suspicious traffic generation...")
        
        end_time = time.time() + duration
        
        while time.time() < end_time and self.running:
            try:
                # Port scanning pattern
                target_ip = random.choice(self.external_ips)
                
                # Sequential port scan
                for port in range(20, 30):
                    if not self.running or time.time() > end_time:
                        break
                        
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.1)
                    
                    try:
                        result = sock.connect_ex((target_ip, port))
                        self.log_info(f"Port Scan: {target_ip}:{port}")
                    except:
                        pass
                    finally:
                        sock.close()
                    
                    time.sleep(0.05)  # Fast scanning
                
                # High frequency connections
                for _ in range(10):
                    if not self.running or time.time() > end_time:
                        break
                        
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.1)
                        port = random.choice([80, 443, 22, 21])
                        sock.connect_ex((target_ip, port))
                        sock.close()
                        self.log_info(f"High Freq: {target_ip}:{port}")
                        time.sleep(0.01)
                    except:
                        pass
                
                time.sleep(random.uniform(5.0, 10.0))
                
            except Exception as e:
                time.sleep(2.0)
    
    def start_traffic_generation(self, duration=60):
        """Start all traffic generation threads"""
        self.running = True
        
        print(f"\n🌐 Starting Realistic Traffic Generation for {duration} seconds...")
        print("=" * 60)
        
        # Create traffic generation threads
        traffic_types = [
            (self.generate_http_traffic, "HTTP/HTTPS Traffic"),
            (self.generate_dns_traffic, "DNS Queries"),
            (self.generate_tcp_connections, "TCP Connections"),
            (self.generate_udp_traffic, "UDP Traffic"),
            (self.generate_ping_traffic, "ICMP Pings"),
            (self.generate_suspicious_traffic, "Suspicious Patterns")
        ]
        
        # Start threads
        for traffic_func, name in traffic_types:
            thread = threading.Thread(
                target=traffic_func, 
                args=(duration,), 
                name=name,
                daemon=True
            )
            thread.start()
            self.threads.append(thread)
            print(f"✅ Started: {name}")
        
        # Wait for completion
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
        finally:
            self.stop_traffic_generation()
    
    def stop_traffic_generation(self):
        """Stop all traffic generation"""
        self.running = False
        print(f"\n🛑 Stopping traffic generation...")
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=2)
        
        print("✅ Traffic generation stopped")

def main():
    generator = RealisticTrafficGenerator()
    
    try:
        # Default 60 seconds, or from command line
        duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
        generator.start_traffic_generation(duration)
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        generator.stop_traffic_generation()

if __name__ == "__main__":
    main()