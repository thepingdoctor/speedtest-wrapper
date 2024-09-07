import sys
import csv
import json
import subprocess
import ipaddress
from typing import Dict, List

def check_deps() -> None:
    """
    Check for the required dependencies ('dig' and 'speedtest').
    Raise an exception if any dependency is missing.
    """
    dependencies = {
        'dig': 'Missing `dig`',
        'speedtest': 'Missing `speedtest` (https://www.speedtest.net/apps/cli)'
    }
    missing = [msg for cmd, msg in dependencies.items() if not shutil.which(cmd)]

    if missing:
        raise Exception('\n'.join(missing))

def ip_to_asn(ip: str) -> int:
    """
    Convert an IP address to its corresponding ASN (Autonomous System Number).
    
    Args:
        ip (str): The IP address to lookup.
    
    Returns:
        int: The ASN associated with the IP address.
    """
    ipa = ipaddress.ip_address(ip)
    reverse_ptr = ipa.reverse_pointer.rstrip('.in-addr.arpa' if ipa.version == 4 else '.in6.arpa')
    lookup_addr = f'{reverse_ptr}.origin{"6" if ipa.version == 6 else ""}.asn.cymru.com.'

    try:
        result = subprocess.check_output(['dig', '+short', lookup_addr, 'TXT']).decode().strip('"').split('|')
        return int(result[0].strip())
    except subprocess.CalledProcessError:
        raise Exception(f"Failed to retrieve ASN for IP: {ip}")
    except (IndexError, ValueError):
        raise Exception(f"Invalid ASN data format for IP: {ip}")

def calculate_mbps(xfer: Dict[str, int]) -> float:
    """
    Calculate Mbps from transfer data.
    
    Args:
        xfer (Dict[str, int]): A dictionary with 'bytes' and 'elapsed' keys.
    
    Returns:
        float: The calculated Mbps.
    """
    bytes_per_second = (xfer['bytes'] / xfer['elapsed']) * 1000
    return bytes_per_second / 125000

def do_speedtest() -> Dict[str, any]:
    """
    Perform a speed test and collect data.
    
    Returns:
        Dict[str, any]: A dictionary with speed test results.
    """
    try:
        result = subprocess.check_output(['speedtest', '--selection-details', '--format=json-pretty']).decode()
        result_json = json.loads(result)
        return {
            'date': result_json['timestamp'],
            'pingLatencyMs': result_json['ping']['latency'],
            'pingJitterMs': result_json['ping']['jitter'],
            'sourceIp': result_json['interface']['externalIp'],
            'destinationIp': result_json['server']['ip'],
            'downloadMbps': calculate_mbps(result_json['download']),
            'uploadMbps': calculate_mbps(result_json['upload']),
        }
    except subprocess.CalledProcessError:
        raise Exception("Failed to perform speed test. Make sure 'speedtest' CLI is installed.")
    except json.JSONDecodeError:
        raise Exception("Failed to parse speed test results.")

def print_result(result: Dict[str, any]) -> None:
    """
    Print the speed test result in CSV format to stdout.
    
    Args:
        result (Dict[str, any]): The speed test result data.
    """
    row = [
        result['date'],
        result['sourceIp'],
        result['destinationIp'],
        result['sourceAsn'],
        result['destinationAsn'],
        result['downloadMbps'],
        result['uploadMbps'],
        result['pingLatencyMs'],
        result['pingJitterMs']
    ]
    writer = csv.writer(sys.stdout)
    writer.writerow(row)

if __name__ == '__main__':
    try:
        check_deps()
        speedtest_data = do_speedtest()
        speedtest_data['sourceAsn'] = ip_to_asn(speedtest_data['sourceIp'])
        speedtest_data['destinationAsn'] = ip_to_asn(speedtest_data['destinationIp'])
        print_result(speedtest_data)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)