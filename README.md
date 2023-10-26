<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
<!-- [![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

 -->

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/associatedpress/">
    <img src="https://www.ap.org/assets/images/ap.svg" alt="AP Logo" width="75" height="88">
  </a>

<h3 align="center">Weather Bot</h3>

  <!-- <p align="center">
    project_description
    <br />
    <a href="https://github.com/github_username/repo_name"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/github_username/repo_name">View Demo</a>
    ·
    <a href="https://github.com/github_username/repo_name/issues">Report Bug</a>
    ·
    <a href="https://github.com/github_username/repo_name/issues">Request Feature</a>
  </p> -->
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#project-objectives">Project Objectives</a></li>
        <li><a href="#how-it-operates">How It Operates</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project
Weather Bot is an automation tool designed to fetch data from the National Hurricane Center and the National Weather Service, identify relevant weather alerts and warnings, and publish weather reports. 

This project was originally built for El Vocero de Puerto Rico in San Juan, Puerto Rico. The Associated Press and the Knight Lab at Northwestern University collaborated to develop this application as part of the Local News AI Initiative, funded by the [John S. and James L. Knight Foundation](https://knightfoundation.org/articles/ai-for-local-news-advancing-business-sustainability-in-newsrooms/), which aims to leverage AI for the benefit of local news.

The development team thanks the staff at [El Vocero de Puerto Rico](https://www.elvocero.com/) for proposing this project, and for their participation, feedback, and encouragement.

### Project Objectives

- **Timely Information:** Ensuring that weather alerts are delivered promptly to keep the community well-informed about potential risks in critical times.
- **Reliable Data:** Sourcing data from government sources to provide the most up-to-date and accurate information.
- **Efficiency:** Utilizing automation to streamline the process of translating weather reports from English to Spanish and writing stories.

### How It Operates

The Weather Bot functions through a simple process:

1. **Data Collection:** The bot continuously monitors data feeds from the National Hurricane Center and the National Weather Service API.
2. **Alert Identification:** The bot uses predefined scenarios to identify weather events that require attention and story generation.
3. **Report Generation:** When an alert is detected, the bot generates comprehensive weather reports capturing the key details.
4. **Publication:** These reports are then published to the CMS of El Vocero and an email notification is sent to the newsroom.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

* [![Python][Python]][Python-url]


<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- GETTING STARTED -->
## Getting Started

This is an example of how you may give instructions on setting up your project locally.
To get a local copy up and running follow these simple example steps.

### Prerequisites

`weatherbot` is developed based on Python. The earliest python version it has been tested with is `3.8.10`

Basic software dependencies are listed in `requirements.txt` and are readily installed from PyPi.

As written, the system depends on three external systems, not including the NWS and NHC feeds:
* Email: the code uses the python standard library to send mail via `SMTP`. Assuming you have access to one, you can simply define the following environment variables, and email sending should work. If necessary variables are not set, the system will log information about the email it would have sent.
  * SMTP_SERVER
  * SMTP_USERNAME
  * SMTP_PASSWORD
  * SENDER_EMAIL

* Posting to Content Management System: the code is tightly coupled to the Blox CMS used by El Vocero. If your organization uses Blox, you probably need to get IP addresses whitelisted; you'll need to edit `blox.py` to change `WS_ROOT` to your organizations API endpoint; and, you'll need to set the environment variables listed below. If the variables are not set, the system will log information about the CMS actions it would have taken.
  * AUTH_USER
  * AUTH_SECRET
* Translation: NWS and NHC bulletins are issued in English. The code is set up to automatically translate text to Spanish, using [DeepL](https://www.deepl.com). To use the translation, you must establish a DeepL account, generate an authentication key, and set it as the value of an environment variable, `DEEPL_AUTH_KEY`. If the environment variable is not set, the system will simply not translate text.

### Installation
1. Clone the repo
   ```sh
   git clone git@github.com:NUKnightLab/weatherbot.git
   ```
2. Install requirements
   ```sh
   pip install -r requirements.txt
   ```
3. Test the code
  ```sh
  python main.py --nws test_files/nws_rip_current.json
  ```

### Testing
Testing the application was challenging, because there are not good archives of bulletins. We've begun developing some testing processes. A handful of test files are in the repository in the `test_files` directory. You can collect others from current data provided from the NWS and NHC.

To run a test, specify the path to an NWS JSON file, an NHC XML file, or both. If you only specify one, the other code path will be ignored. (That is, it won't go out to get live data.) You may want to adjust logging configuration, currently in `main.py`. (In the future, logging configuration should probably be externalized to a configuration file.)

Example test commands:
  ```sh
  python main.py --nws test_files/nws_rip_current.json
  python main.py --nhc test_files/nhc_franklin_tropical_storm_watch.xml
  ```






<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- LICENSE -->
## License

Distributed under the GNU GENERAL PUBLIC LICENSE. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

*The Associated Press does not provide technical support for this open-source application.*

Joe Germuska - [@JoeGermuska](https://github.com/JoeGermuska) - JoeGermuska@northwestern.edu

Project Link: [https://github.com/NUKnightLab/weatherbot](https://github.com/NUKnightLab/weatherbot)


<!-- ORIGINAL DEVELOPERS -->
### Original Developers

* Mame Coumba Ka - [@coumbaK](https://github.com/coumbaK) - Northwestern University
* Maria Ximena Aragon - Northwestern University

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/github_username/repo_name.svg?style=for-the-badge
[contributors-url]: https://github.com/github_username/repo_name/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/github_username/repo_name.svg?style=for-the-badge
[forks-url]: https://github.com/github_username/repo_name/network/members
[stars-shield]: https://img.shields.io/github/stars/github_username/repo_name.svg?style=for-the-badge
[stars-url]: https://github.com/github_username/repo_name/stargazers
[issues-shield]: https://img.shields.io/github/issues/github_username/repo_name.svg?style=for-the-badge
[issues-url]: https://github.com/github_username/repo_name/issues
[license-shield]: https://img.shields.io/github/license/github_username/repo_name.svg?style=for-the-badge
[license-url]: https://github.com/github_username/repo_name/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/linkedin_username
[product-screenshot]: images/screenshot.png
[Next.js]: https://img.shields.io/badge/next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white
[Next-url]: https://nextjs.org/
[Python]:https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]:https://www.python.org/
