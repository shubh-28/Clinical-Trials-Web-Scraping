import os
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.font import Font
from PIL import Image, ImageTk

class ClinicalTrialsScraper:
    def __init__(self, master):
        self.master = master
        self.master.title("Clinical Trials Scraper")

        # Maximize the window to fit the screen
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        self.master.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # Create gradient background
        self.canvas = tk.Canvas(master)
        self.canvas.pack(fill="both", expand=True)
        self.create_gradient(self.canvas, ["#8ce2ee", "#93bae1", "#8984d6", "#7251b2", "#642e7c"])

        # Custom Font
        self.custom_font = Font(family="Montserrat", size=int(master.winfo_height() / 25))  # Adjust font size dynamically

        # White frame for input and output
        self.frame = tk.Frame(master, bg='white', padx=20, pady=20)
        self.frame.place(relx=0.5, rely=0.5, anchor='center')

        # Prussian blue section for user input with gradient
        self.inner_canvas = tk.Canvas(self.frame, width=600, height=200)
        self.inner_canvas.pack(fill="both", expand=True)
        self.create_inner_gradient(self.inner_canvas, ["#003153", "#00509E"])

        self.input_frame = tk.Frame(self.inner_canvas, bg='white', padx=10, pady=10)
        self.input_frame.place(relx=0.5, rely=0.5, anchor='center')

        # Input keyword
        self.label = ttk.Label(self.input_frame, text="Enter the keyword to search:", background='#00509E', foreground='white', font=self.custom_font)
        self.label.grid(row=0, column=0, padx=5, pady=5)
        
        self.entry = ttk.Entry(self.input_frame, width=40, font=self.custom_font)
        self.entry.grid(row=1, column=0, padx=5, pady=5)
        
        self.button = ttk.Button(self.input_frame, text="Start Scraping", command=self.start_scraping)
        self.button.grid(row=2, column=0, pady=10)
        
        # Progress bar and result label
        self.progress = ttk.Progressbar(self.frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)
        
        self.result_label = ttk.Label(self.frame, text="", background='white', font=self.custom_font)
        self.result_label.pack(pady=10)
        
        self.driver = None

    def create_gradient(self, canvas, colors):
        width = self.master.winfo_screenwidth()
        height = self.master.winfo_screenheight()
        num_colors = len(colors)
        (r1, g1, b1) = self.master.winfo_rgb(colors[0])
        (r2, g2, b2) = self.master.winfo_rgb(colors[-1])
        r_ratio = float(r2 - r1) / height
        g_ratio = float(g2 - g1) / height
        b_ratio = float(b2 - b1) / height

        for i in range(height):
            r = int(r1 + (r_ratio * i))
            g = int(g1 + (g_ratio * i))
            b = int(b1 + (b_ratio * i))
            color = f'#{r:04x}{g:04x}{b:04x}'
            canvas.create_line(0, i, width, i, fill=color, width=1)

    def create_inner_gradient(self, canvas, colors):
        width = 600
        height = 200
        (r1, g1, b1) = self.master.winfo_rgb(colors[0])
        (r2, g2, b2) = self.master.winfo_rgb(colors[-1])
        r_ratio = float(r2 - r1) / height
        g_ratio = float(g2 - g1) / height
        b_ratio = float(b2 - b1) / height

        for i in range(height):
            r = int(r1 + (r_ratio * i))
            g = int(g1 + (g_ratio * i))
            b = int(b1 + (b_ratio * i))
            color = f'#{r:04x}{g:04x}{b:04x}'
            canvas.create_line(0, i, width, i, fill=color, width=1)

    def start_scraping(self):
        text = self.entry.get()
        if not text:
            messagebox.showwarning("Input Error", "Please enter a keyword.")
            return
        
        self.progress["value"] = 0
        self.result_label.config(text="")
        
        self.driver = self.setup_webdriver()
        
        try:
            nct_data = self.scrape_data(text)
            if nct_data:
                file_path = self.save_to_excel(nct_data)
                self.result_label.config(text=f"Scraping completed. Data saved to {file_path}")
            else:
                self.result_label.config(text="No data found.")
        except Exception as e:
            self.result_label.config(text=f"Error: {e}")
        finally:
            if self.driver:
                self.driver.quit()

    def setup_webdriver(self):
        service = Service(executable_path="chromedriver.exe")
        driver = webdriver.Chrome(service=service)
        return driver

    def scrape_data(self, text):
        self.driver.get("https://clinicaltrials.gov/")
        
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "advcond"))
        )
        input_element = self.driver.find_element(By.NAME, "advcond")
        input_element.send_keys(text + Keys.ENTER)
        
        time.sleep(10)
        
        try:
            results_text = self.driver.find_element(By.CSS_SELECTOR, "p.shown-range.font-body-md.ng-star-inserted").text
            total_studies = int(re.search(r'out of ([\d,]+) studies', results_text).group(1).replace(',', ''))
        except Exception as e:
            print(f"Error extracting number of studies: {e}")
            total_studies = 0
        
        studies_per_page = 100
        num_pages = (total_studies // studies_per_page) + 1
        
        all_nct_ids = []
        
        for page_num in range(num_pages):
            url = f"https://clinicaltrials.gov/search?cond={text}&limit=100&rank={page_num*100+1}"
            self.driver.get(url)
            nct_ids = self.extract_nct_ids()
            all_nct_ids.extend(nct_ids)
        
        data = []
        for rank, nct_id in enumerate(all_nct_ids, start=1):
            study_url = f"https://clinicaltrials.gov/study/{nct_id}?cond={text}&limit=100&rank={rank}"
            study_details = self.scrape_study_details(study_url)
            study_details["NCT-ID"] = nct_id
            study_details["URL"] = study_url
            data.append(study_details)
            
            self.progress["value"] = (rank / len(all_nct_ids)) * 100
            self.master.update_idletasks()
        
        return data
    
    def extract_nct_ids(self):
        time.sleep(5)
        nct_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.nct-id")
        return [elem.text for elem in nct_elements]
    
    def scrape_study_details(self, url):
        self.driver.get(url)
        time.sleep(3)
        details = {}
        try:
            details['Study Start'] = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Study Start')]/following-sibling::span").text
        except:
            details['Study Start'] = "N/A"
        try:
            details['Primary Completion'] = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Primary Completion')]/following-sibling::span").text
        except:
            details['Primary Completion'] = "N/A"
        try:
            details['Study Completion'] = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Study Completion')]/following-sibling::span").text
        except:
            details['Study Completion'] = "N/A"
        try:
            details['Enrollment'] = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Enrollment')]/following-sibling::div/span").text
        except:
            details['Enrollment'] = "N/A"
        try:
            details['Study Type'] = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Study Type')]/following-sibling::ctg-enum-value/span").text
        except:
            details['Study Type'] = "N/A"
        try:
            details['Phase'] = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Phase')]/following-sibling::ctg-enum-value/span").text
        except:
            details['Phase'] = "N/A"
        
        return details
    
    def save_to_excel(self, data):
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False)
            return file_path
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = ClinicalTrialsScraper(root)
    root.mainloop()


