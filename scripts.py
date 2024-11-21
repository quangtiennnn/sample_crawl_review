import pandas as pd
import time
import os
import csv
import pandas as pd
from tqdm import tqdm
from urllib.parse import urlparse, urlunparse
import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Set Chrome options:
chrome_options = Options()
# chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox') 
chrome_options.add_argument("--incognito")
# chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-application-cache")
chrome_options.add_argument("--force-device-scale-factor=0.75")  # Set zoom level to 125%
# chrome_options.add_argument("--high-dpi-support=1")  # Ensure DPI support
chrome_options.add_argument("--disable-infobars")  # Disable info bars
chrome_options.add_argument("--disable-extensions")  # Disable extensions
# chrome_options.add_argument("--disable-cache")
chrome_options.add_argument("--disk-cache-size=0")

global random_duration
random_duration = random.uniform(3, 7)


## GET LINKS
def url_edited(url):
    try:
        parsed_url = urlparse(url)
        # new_path = "/vi-vn" + parsed_url.path
        return urlunparse(parsed_url._replace(query=""))
    except Exception as e:
        # print(f"Error editing URL: {url}")
        return ""

def get_url(url):
    try:
        driver = webdriver.Chrome()
        driver.get(url)
        time.sleep(random_duration) # Ensure no detection
        elem = driver.find_element(By.CSS_SELECTOR, "a[data-element-name='property-card-content']")
        href = elem.get_attribute('href')
        driver.close()
        return url_edited(href)
    except Exception as e:
        # print(f"Error fetching URL: {url}")
        return ""


## GET REVIEWS:
### GET INFORMATIONS:
def parse_text_to_dict(raw_text):
    # Step 1: Clean the text by removing excess newlines and spaces
    cleaned_text = raw_text.replace("\n", " ").strip()

    # Step 2: Extract the key (first meaningful phrase)
    key_end_index = cleaned_text.find("  ")  # Find double spaces as the delimiter for the key
    if key_end_index != -1:
        key = cleaned_text[:key_end_index].strip().lower()  # Extract the key and convert to lowercase
        content = cleaned_text[key_end_index:].strip()
    else:
        key = cleaned_text.lower()  # Convert the whole text to lowercase if no delimiter
        content = ""

    # Step 3: Parse the content into a list of values
    # Remove multiple spaces and clean the items, then convert to lowercase
    values = [item.strip().lower() for item in content.split("                      ") if item.strip()]

    # Step 4: Return the dictionary
    return {key: values}

def get_information(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    
    # # Find all elements with class "Box-sc-kv6pi1-0 dtSdUZ"
    elements_dtSdUZ = soup.find_all("div", class_="Box-sc-kv6pi1-0 dtSdUZ")
    
    # Find all elements with class "Box-sc-kv6pi1-0 cTxLvk FeatureGroup"
    elements_FeatureGroup = soup.find_all("div", class_="Box-sc-kv6pi1-0 cTxLvk FeatureGroup")
    
    data = {}
    
    # Assuming elements_FeatureGroup contains the relevant data sections to scrape
    for feature_group in elements_FeatureGroup:
        # Find all elements within the feature group
        elems = feature_group.find_all("div", class_="Box-sc-kv6pi1-0 dtSdUZ")
    
        for elem in elems:
            # Parse the element using BeautifulSoup
            elem = BeautifulSoup(elem.prettify(), "html.parser")
            parsed_data = parse_text_to_dict(elem.text)
    
            # Merge the parsed data into the main dictionary
            data.update(parsed_data)
    
    # The `data` dictionary now contains the merged key-value pairs
    return data

### GET REVIEWS SUMMARY:
from bs4 import BeautifulSoup

def get_review_summary(page_source):
    soup = BeautifulSoup(page_source, 'html.parser')

    # Initialize the result dictionary
    review_summary = {}

    # Extract overall score
    overall_score_section = soup.find('div', class_='Review-reviewBranding')
    if overall_score_section:
        overall_score = overall_score_section.find('div', class_='ReviewScore-Number')
        review_summary['overall_score'] = overall_score.text.strip() if overall_score else ''

    # Extract total number of reviews
    total_reviews_section = overall_score_section.find('span', class_='text') if overall_score_section else None
    review_summary['number_reviews_total'] = total_reviews_section.get_text(strip=True) if total_reviews_section else ''
    
    class_type_primary = ['ae7b2-box']  # First class type
    class_type_secondary = ['a23d5-box']  # Second class type
    
    # Try finding scores with the primary class type
    scores = soup.find_all('li', class_= class_type_primary)
    
    # If no results are found, try the secondary class type
    if not scores:
        scores = soup.find_all('li', class_= class_type_secondary)
    
    # Initialize review_summary dictionary
    review_summary = {}
    
    for score in scores:
        # Extract category name
        category_span = score.find('span', class_='zNgxw')
        category = category_span.text.strip().lower().replace(' ', '_') if category_span else None
    
        # Extract score value
        value_span = score.find('span', class_='huxGky') or score.find('span', class_='inJLAi')
        value = value_span.text.strip() if value_span else None
    
        if category and value:
            review_summary[category] = value

    # Extract actual number of reviews
    actual_reviews_section = soup.find('span', class_='Review__SummaryContainer--left Review__SummaryContainer__Text')
    if actual_reviews_section:
        review_summary['number_reviews_actual'] = actual_reviews_section.text.strip()

    return review_summary
    
    
## GET REVIEWS:

def get_reviews(page_source):
    """
    Extracts reviews, positive and negative comments, and responses from the provided HTML content.
    
    Args:
        html_content (str): The raw HTML content as a string.
    
    Returns:
        list: A list of dictionaries containing review details, including positive/negative comments and responses.
    """
    # Parse the HTML content
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # Initialize the list to hold all reviews
    reviews = []
    
    # Extract all review elements
    for review_div in soup.find_all('div', {'data-element-name': 'review-comment', 'data-review-comment-type': 'comment'}):
        review_data = {}
        
        # Review ID
        review_data['review_id'] = review_div.get('data-review-id')
        
        # Score and Score Text
        score = review_div.select_one('.Review-comment-leftScore')
        score_text = review_div.select_one('.Review-comment-leftScoreText')
        review_data['score'] = score.text.strip() if score else ''
        review_data['score_text'] = score_text.text.strip() if score_text else ''
        
        # Reviewer Name and Nationality
        reviewer_info = review_div.select_one('div[data-info-type="reviewer-name"]')
        if reviewer_info:
            review_data['reviewer_name'] = reviewer_info.find('strong').text.strip() if reviewer_info.find('strong') else ''
            review_data['reviewer_nationality'] = reviewer_info.find_all('span')[-1].text.strip() if len(reviewer_info.find_all('span')) > 1 else ''
        
        # Group Name
        group_name = review_div.select_one('div[data-info-type="group-name"] span')
        review_data['group_name'] = group_name.text.strip() if group_name else ''
        
        # Stay Details
        stay_detail = review_div.select_one('div[data-info-type="stay-detail"] span')
        review_data['stay_detail'] = stay_detail.text.strip() if stay_detail else ''
        
        # Review Title and Comment
        title = review_div.find(('h4', 'h3'), {'data-testid': 'review-title'})
        
        comment = review_div.select_one('p[data-testid="review-comment"]')
        
        review_data['review_title'] = title.text.strip() if title else ''        
        
        review_data['review_comment'] = comment.text.strip() if comment else ''
        
        # Positive Comment
        positive_comment = review_div.select_one('div[data-type="positive"]')
        review_data['positive_comment'] = positive_comment.text.strip() if positive_comment else ''
        
        # Negative Comment
        negative_comment = review_div.select_one('div[data-type="negative"]')
        review_data['negative_comment'] = negative_comment.text.strip() if negative_comment else ''
        
        # Review Date
        review_date = review_div.select_one('.Review-statusBar-date')
        review_data['review_date'] = review_date.text.strip() if review_date else ''
        
        # Nested Response
        response_div = review_div.find('div', {'data-review-comment-type': 'response'})
        if response_div:
            response_text = response_div.select_one('.Review-response-text')
            review_data['response'] = response_text.text.strip() if response_text else ''
        else:
            review_data['response'] = ''  # Leave blank if no response

        # Append to the list
        reviews.append(review_data)
    
    return reviews

