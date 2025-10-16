# app.py
# Bhai, pehle yeh sab cheezein install kar lena: pip install -r requirements.txt
from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import logging
import time
import json

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

ACADEMIA_URL = "https://academia.srmist.edu.in/accounts/p/10002227248/signin?serviceurl=https%3A%2F%2Facademia.srmist.edu.in%2Fportal%2Facademia-academic-services%2FredirectFromLogin"


def scrape_srm_data():
    """
    Yeh function আসল kaam karega. Login karke data nikalega.
    Credentials ab yahan hardcoded hain.
    New logic based on API calls.
    """
    username = "kp7474@srmist.edu.in"
    password = "Kulbhushan@2025"

    with requests.Session() as session:
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.8',
            'Connection': 'keep-alive',
            'Host': 'academia.srmist.edu.in',
            'Origin': 'https://academia.srmist.edu.in',
            'sec-ch-ua': '"Brave";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
        })

        try:
            logging.info("Step 1: Fetching initial page and cookies from specific sign-in URL...")
            initial_response = session.get(ACADEMIA_URL, timeout=15)
            logging.info(f"Initial page loaded. Final URL is: {initial_response.url}")

            csrf_token_cookie = session.cookies.get('iamcsr')
            if not csrf_token_cookie:
                return {'status': 'error', 'message': 'Pehli request ke liye CSRF token cookie nahi mila.'}
            logging.info("CSRF token for lookup fetched successfully.")

            lookup_url = f"https://academia.srmist.edu.in/accounts/p/40-10002227248/signin/v2/lookup/{username}"

            cli_time = int(time.time() * 1000)
            lookup_payload = {
                'mode': 'primary',
                'cli_time': cli_time,
                'orgtype': '40',
                'service_language': 'en',
                'serviceurl': 'https://academia.srmist.edu.in/portal/academia-academic-services/redirectFromLogin'
            }

            lookup_headers = {
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'Referer': initial_response.url,
                'x-zcsrf-token': f"iamcsrcoo={csrf_token_cookie}"
            }

            logging.info(f"Step 2: Performing user lookup for {username} with CSRF token...")
            lookup_response = session.post(lookup_url, data=lookup_payload, headers=lookup_headers, timeout=15)
            lookup_response.raise_for_status()

            lookup_data = lookup_response.json()
            if lookup_data.get("status_code") != 201:
                return {'status': 'error', 'message': f'User lookup fail ho gaya: {lookup_data.get("message")}'}

            logging.info("User lookup successful.")

            identifier = lookup_data['lookup']['identifier']
            digest = lookup_data['lookup']['digest']

            password_url = (
                f"https://academia.srmist.edu.in/accounts/p/40-10002227248/signin/v2/primary/{identifier}/password"
                f"?digest={digest}&cli_time={cli_time}&orgtype=40&service_language=en"
                "&serviceurl=https%3A%2F%2Facademia.srmist.edu.in%2Fportal%2Facademia-academic-services%2FredirectFromLogin")

            password_payload = {"passwordauth": {"password": password}}

            password_headers = {
                'Content-Type': 'application/json;charset=UTF-8',
                'Referer': initial_response.url,
                'x-zcsrf-token': f"iamcsrcoo={csrf_token_cookie}"
            }

            logging.info("Step 3: Submitting password...")
            password_response = session.post(password_url, json=password_payload, headers=password_headers, timeout=15,
                                             allow_redirects=True)
            password_response.raise_for_status()

            try:
                pass_resp_data = password_response.json()
                if "error" in pass_resp_data:
                    logging.warning(f"Login failed: {pass_resp_data.get('error', {}).get('message')}")
                    return {'status': 'error', 'message': 'Bhai, User ID ya Password galat hai.'}
            except json.JSONDecodeError:
                logging.info("Password response was not JSON, assuming successful redirect.")
                pass

            logging.info("Password submitted, session should be authenticated.")

            logging.info("Step 4: Fetching dashboard data...")
            dashboard_url = "https://academia.srmist.edu.in/portal/academia-academic-services"
            dashboard_response = session.get(dashboard_url, timeout=15)
            dashboard_response.raise_for_status()

            dashboard_soup = BeautifulSoup(dashboard_response.text, 'html.parser')

            student_name_tag = dashboard_soup.find('span', {'id': 'ccContent_lblStudentName'})
            reg_no_tag = dashboard_soup.find('span', {'id': 'ccContent_lblRegisterNumber'})
            program_tag = dashboard_soup.find('span', {'id': 'ccContent_lblProgram'})

            student_name = student_name_tag.text.strip() if student_name_tag else "Not Found"
            reg_no = reg_no_tag.text.strip() if reg_no_tag else "Not Found"
            program = program_tag.text.strip() if program_tag else "Not Found"

            if student_name == "Not Found":
                logging.error("Could not find student data. Login might have failed silently.")
                return {'status': 'error',
                        'message': 'Login toh ho gaya shayad, lekin dashboard se data nahi mila. Page structure check kar.'}

            logging.info(f"Data scraped: Name - {student_name}, RegNo - {reg_no}")

            scraped_data = {
                "studentName": student_name,
                "registerNumber": reg_no,
                "program": program
            }

            return {'status': 'success', 'data': scraped_data}

        except requests.exceptions.Timeout:
            logging.error("Request timed out. Website bohot slow hai ya block kar rahi hai.")
            return {'status': 'error', 'message': 'Website se connect karne me time-out ho gaya, bhai.'}
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error: {e}")
            return {'status': 'error', 'message': f'Website tak nahi pahunch pa raha, bhai. Error: {e}'}
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
            return {'status': 'error', 'message': f'Kuch toh fulta jhol ho gaya: {e}'}


@app.route('/api/srm-data', methods=['POST'])
def get_srm_data():
    """
    Yeh hai hamara API endpoint. Ab yeh body se data nahi leta.
    """
    logging.info("Received request to fetch SRM data with hardcoded credentials.")
    result = scrape_srm_data()

    if result['status'] == 'success':
        return jsonify(result), 200
    else:
        status_code = 401 if 'galat hai' in result.get('message', '') else 500
        return jsonify(result), status_code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

