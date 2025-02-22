from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup
import openai
import toml

import re
import requests
from enum import Enum
import argparse
import json
import os

# Enum for different types of articles
class TitleType(Enum):
    TOP_10 = 0
    TOP_15 = 1
    TOP_20 = 2
    EXPLAINED = 3
    QUESTION = 4
    GENERAL = 5
    TOP_5 = 6


output_example = """
Top 10 Shark Tank Products the Sharks Regret Taking
1. Kate App: A privacy app that allows users to hide communications from specific contacts. The app is no longer available.
2. Cubits: A construction toy that allows kids to build various structures. The company is still in business but their social media presence is inactive.
3. 365: A subscription service for men's underwear. The company was sold off and eventually closed in 2019.
4. Haikon: A fire hose attachment that makes it easier to connect hoses. The company's social media presence is inactive and their online store is missing.
5. Show No Towels: A changing towel that can be used as a poncho. The company was sold off and eventually closed in 2019.
6. Night Runner: A shoe light that provides visibility in the dark. The company is still in business and has expanded their product line.
7. The Body Jack: An exercise machine that helps users lose weight. The company is no longer in business and their social media presence is inactive.
8. Sweet Balls: A subscription-based service that delivers boxes of toys to customers every month. The company went bankrupt in 2012.
9. Toyguru: A subscription-based service that delivers boxes of toys to customers every month. The company went bankrupt in 2012.
10. Breathometer: A smartphone-compatible breathalyzer. The product was discontinued and the company was required to refund customers who had purchased it.
"""


def load_secret(path="."):
    path = f"{path}/secret.toml"
    with open(path, "r") as f:
        keys = toml.loads(f.read())
        openai.api_key = keys["openai-key"]


def title_to_prompt(title: str, title_type: TitleType = TitleType.GENERAL):

    if title_type == TitleType.TOP_10:
        return f"Summarize the following transcript of a video titled '{title}' into to a numbered list.\nInclude a short description for each item."
    elif title_type == TitleType.TOP_15:
        return f"Summarize the following transcript of a 'top 15' video titled '{title}' to a list.\nInclude a short description for each item."
    elif title_type == TitleType.TOP_20:
        return f"Summarize the following transcript of a 'top 20' video titled '{title}' to a list.\nInclude a short description for each item."
    elif title_type == TitleType.EXPLAINED:
        return f"Summarize the following transcript of a video titled '{title}'. Keep it fewer than 200 words."
    elif title_type == TitleType.QUESTION:
        return f"Summarize the following transcript of a video so it answers the question '{title}' in fewer than 200 words."
    elif title_type == TitleType.GENERAL:
        return f"Summarize the following transcript of a video, titled '{title}', to fewer than 200 words."
    elif title_type == TitleType.TOP_5:
        return f"Summarize the following transcript of a 'top 5' video titled '{title}' to a list.\nInclude a short description for each item."


def example_by_type(title_type: TitleType):
    if title_type == TitleType.TOP_10:
        return f"\nExample Output:\n{output_example}\n"
    else:
        return ""


def gpt3_summarize(title, title_type, text):
    prompt = title_to_prompt(title, title_type)
    example = example_by_type(title_type)
    ask_text = f"{prompt}\n{example}\nInput:\n{text}\n\nOutput:"

    print(f"Querying OpenAI for summary of '{title}'...")
    result = openai.Completion.create(
        engine="text-davinci-002", temperature=0, max_tokens=512, prompt=ask_text
    )
    print(f"Done!")
    return ask_text, result.choices[0]["text"]


def gpt3_summarize_cont(title, title_type, text, summary):
    ask_text = f"The following is a transcript of the video '{title}':\n{text}\n\nNow, base don the transcript, continue writing summary below:\n{summary}"

    print(f"Querying OpenAI for summary of '{title}'...")
    result = openai.Completion.create(
        engine="text-davinci-002", temperature=0, max_tokens=512, prompt=ask_text
    )
    print(f"Done!")
    return ask_text, result.choices[0]["text"]


def gpt3_summarize_distill(title, title_type, summary):
    ask_text = f"Summarize the following transcript of a video titled '{title}'. Keep it short as possible.\n\nTranscript:\n{summary}\n\nOutput:"

    print(f"Querying OpenAI for summary of '{title}'...")
    result = openai.Completion.create(
        engine="text-davinci-002", temperature=0, max_tokens=512, prompt=ask_text
    )
    print(f"Done!")
    return ask_text, result.choices[0]["text"]


def summarize(video_id: str, title_type: TitleType = TitleType.GENERAL):

    # Get the transcript
    cc = YouTubeTranscriptApi.get_transcript(video_id)
    cc_texts = [c["text"] for c in cc]
    text = " ".join(cc_texts)
    text = text.replace("\n", " ")  # Remove newlines
    orig_text = re.sub(r"\s+", " ", text)  # Remove double spaces

    text = orig_text

    # Get the title of the YouTube video
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    r = requests.get(video_url)
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("title").text[:-10]

    # Get the thumbnail
    thumbnail_url = "https://img.youtube.com/vi/" + video_id + "/0.jpg"

    print(f"Video ID:    {video_id}")
    print(f"Video url:   {video_url}")
    print(f"Thumbnail:   {thumbnail_url}")
    print(f"Title:       {title}")
    print(f"Title type:  {title_type}")
    dots = "..." if len(text) > 100 else ""
    print(f"Text:        {text[:100]}{dots}")

    load_secret()

    tokens = text.split(" ")
    MAX_TOKENS = 2500
    is_split = len(tokens) > MAX_TOKENS
    if is_split:
        print("Input is very long, splitting into chunks...")
        chunks = [tokens[i : i + MAX_TOKENS] for i in range(0, len(tokens), MAX_TOKENS)]
        chunks = [" ".join(c) for c in chunks]
        prompts = []
        summaries = []
        for chunk in chunks:
            if len(summaries) == 0:
                prompt, summary = gpt3_summarize(title, title_type, chunk)
            else:
                summary_cat = " ".join(summaries)
                prompt, summary = gpt3_summarize_cont(
                    title, title_type, chunk, summary_cat
                )
            prompts.append(prompt)
            summaries.append(summary)
        summary = " ".join(summaries)
        print(f"Summary: \n{summary}")
        summary_tokens = summary.split(" ")
        if len(summary_tokens) > 400:
            print("Summary is too long, distilling...")
            prompt, summary = gpt3_summarize_distill(title, title_type, summary)
            print(f"Distilled summary: \n{summary}")
            prompts.append(prompt)

    else:
        prompt, summary = gpt3_summarize(title, title_type, text)
        prompts = [prompt]
        print(f"Summary: \n{summary}")

    # Save the result into a json file
    result = {
        "video_id": video_id,
        "video_url": video_url,
        "title": title,
        "title_type": title_type.name,
        "orig_text": orig_text,
        "proc_text": text,
        "prompts": prompts,
        "summary": summary,
    }
    result_path = "./results"
    if not os.path.exists(result_path):
        os.mkdir(result_path)
    result_file = os.path.join(result_path, f"{video_id}.json")
    with open(result_file, "w") as f:
        json.dump(result, f, indent=4)

    return result

    # # convert newlines to html breaks
    # summary = summary.replace("\n", "<br>")

    # html = f"""
    # <h1>{title}</h1>
    # <img src="{thumbnail_url}">
    # <p>{summary}</p>
    # """

    # with open("summary.html", "w") as f:
    #     f.write(html)


def title_type_str_to_enum(title_type_str: str):
    if title_type_str == "top10":
        return TitleType.TOP_10
    elif title_type_str == "top5":
        return TitleType.TOP_5
    elif title_type_str == "top15":
        return TitleType.TOP_15
    elif title_type_str == "top20":
        return TitleType.TOP_20
    elif title_type_str == "explained":
        return TitleType.EXPLAINED
    elif title_type_str == "question":
        return TitleType.QUESTION
    elif title_type_str == "general":
        return TitleType.GENERAL
    else:
        raise Exception(f"Unknown title type: {title_type_str}")


def main():
    parser = argparse.ArgumentParser(description="Summarize a YouTube video with GPT-3")
    parser.add_argument(
        "--video_id", type=str, required=True, help="Video id of YouTube video"
    )
    parser.add_argument(
        "--title_type",
        type=str,
        default="general",
        help='Title type of the video. Choose from "top10", "top15", "top20", "explained", "question", "general"',
    )
    args = parser.parse_args()

    v_id = args.video_id
    if v_id[0] == "@":
        v_id = v_id[1:]
    t_type = title_type_str_to_enum(args.title_type)
    summarize(v_id, t_type)


if __name__ == "__main__":
    main()
