# web scraping

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# html parsing
from bs4 import BeautifulSoup

# dataframes
import pandas as pd

# async
import asyncio
import nest_asyncio 
import aiohttp
import os

# terminal formatting
from rich.progress import track
from rich.console import Console
from rich.table import Table

nest_asyncio.apply()

# instantiate global variables
df = pd.DataFrame(columns=["Title", "Location", "Company", "Link", "Description"])
console = Console()
table = Table(show_header=True, header_style="bold")

#Specify directory to sabe exports
EXPORT_DIR = "/Users/gerardroca/Documents/IRONHACK/PROJECTS/genAI-RAG/data/"

# Ensure the export directory exists
os.makedirs(EXPORT_DIR, exist_ok=True)


def get_user_input():
    console.print("Enter Job Title :", style="bold green", end=" ")
    job_title = input().strip()
    console.print("Enter Job Location :", style="bold green", end=" ")
    job_location = input().strip()
    return job_title, job_location


def driver_options():
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    return driver


async def fetch_page_content(session, url):
    async with session.get(url) as response:
        return await response.text()
    


async def scrape_job_description(url, session):
    html = await fetch_page_content(session, url)
    soup = BeautifulSoup(html, "html.parser")
    try:
        job_description = soup.find(
            "div", class_="show-more-less-html__markup"
        ).text.strip()
        return job_description
    except AttributeError:
        return ""



async def scrape_linkedin(job_title, job_location):  
    global df
    driver = driver_options()
    counter = 0
    page_counter = 1
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                driver.get(
                    f"https://www.linkedin.com/jobs/search/?keywords={job_title}&location={job_location}&start={counter}"
                )

                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")

                ul_element = soup.find("ul", class_="jobs-search__results-list")
                if not ul_element:
                    break

                li_elements = ul_element.find_all("li")

                for item in track(li_elements, description=f"LinkedIn - Page: {page_counter}"):
                    job_title = item.find("h3", class_="base-search-card__title").text.strip()
                    job_location = item.find("span", class_="job-search-card__location").text.strip()
                    job_company = item.find("h4", class_="base-search-card__subtitle").text.strip()
                    job_link = item.find_all("a")[0]["href"]

                    job_description = await scrape_job_description(job_link, session)

                    if job_title and job_location and job_company and job_link:
                        df = pd.concat(
                            [
                                df,
                                pd.DataFrame(
                                    {
                                        "Title": [job_title],
                                        "Location": [job_location],
                                        "Company": [job_company],
                                        "Link": [job_link],
                                        "Description": [job_description],
                                    }
                                ),
                            ]
                        )

                console.print("Scrape Next Page? (y/n) :", style="bold yellow", end=" ")
                continue_input = input()

                if continue_input.lower() == "n":
                    break

                counter += 25
                page_counter += 1

            except Exception as e:
                console.print(f"An error occurred: {e}", style="bold red")
                break

        driver.quit()


def save_to_txt(job_title, job_location):
    file_name = f"{job_title}_{job_location}_jobs.txt"
    file_path = os.path.join(EXPORT_DIR, file_name)
    with open(file_name, "w", encoding="utf-8") as file:
        for index, row in df.iterrows():
            file.write(f"Title: {row['Title']}\n")
            file.write(f"Company: {row['Company']}\n")
            file.write(f"Location: {row['Location']}\n")
            file.write(f"Link: {row['Link']}\n")
            file.write(f"Description: {row['Description']}\n")
            file.write("\n" + "-"*50 + "\n\n")

async def main():
    job_title, job_location = get_user_input()
    await scrape_linkedin(job_title, job_location)

    # create table
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Location")
    table.add_column("Link")
    table.add_column("Description")


    # loop over dataframe and print rich table
    for index, row in df.iterrows():
        table.add_row(
            row['Title'],
            row['Company'],
            row['Location'],
            row['Link'],
            (row['Description'][:20] + "...") if row['Description'] else "N/A"
        )

    console.print(table)

    console.print("Save results locally? (y/n) :", style="bold yellow", end=" ")
    continueInput = input()

    if continueInput == "y":
        df.to_csv(f"{job_title}_{job_location}_jobs.csv", index=False)
        save_to_txt(job_title, job_location)


if __name__ == "__main__":
    # run main function
    if not asyncio.get_event_loop().is_running(): 
        asyncio.run(main())
    else:
        nest_asyncio.apply()  
        asyncio.run(main()) 
