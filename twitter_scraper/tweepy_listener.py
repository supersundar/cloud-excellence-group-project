import boto3
from boto3.dynamodb.conditions import Attr,Key
from botocore.exceptions import ClientError
import tweepy
import os
import sys
import time
from textblob import TextBlob
from decimal import Decimal
from datetime import date,datetime,timedelta
import traceback
import cld3

class TwitterStreamListener(tweepy.StreamListener):

    def __init__(self, max_tweets_per_minute, sns_error_topic=None):
        super(TwitterStreamListener, self).__init__()
        # self.current_file_name, self.current_path = self.new_paths()
        # self.file_size = file_cutoff_size*1000000
        # self.s3 = boto3.client('s3')
        # self.s3_bucket = s3_bucket
        # if not os.path.exists("./tweet_files"):
        #     os.mkdir("./tweet_files")

        # if sns_error_topic:
        #     self.sns = boto3.resource('sns', region_name='us-east-2')
        #     self.topic = self.sns.Topic(sns_error_topic)

        self.last_updated_sysinfo = datetime.now()
        self.update_sysinfo = False

        self.error_count = 0

        self.all_tweets = []

        self.max_tweets_per_minute = max_tweets_per_minute
        self.curr_tweet_count = 0
        self.curr_minute = datetime.now()+timedelta(minutes=1)

    def check_rate_limit(self):
        if self.curr_minute > datetime.now():
            if self.curr_tweet_count < self.max_tweets_per_minute:
                return False
            else:
                return True
        else:
            self.curr_minute = datetime.now()+timedelta(minutes=1)
            self.curr_tweet_count = 1
            return False

    def on_status(self, status):
        try:
            tweet = status.__dict__['_json']
            self.curr_tweet_count += 1
            limited = self.check_rate_limit()
            if not limited:
                self.all_tweets.append(tweet)
                print(len(self.all_tweets))

            # only update every 10 minutes just as a sanity check
            if datetime.now() > self.last_updated_sysinfo + timedelta(minutes=10):
                self.last_updated_sysinfo = datetime.now()
                self.update_sysinfo = True
                print("ready to update sysinfo")

            self.error_count = 0
        except Exception as e:
            print(traceback.print_exc())
            self.error_count += 1
            if self.error_count > 3:
                print("Hit three errors. Exiting.")
                # self.topic.publish(Message=f"Hit 3 errors in a row in on_status\nScraper shutdown time = {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}")
                sys.exit()

    def on_error(self, status_code):
        if status_code == 420 or status_code==429:
            #returning False in on_error disconnects the stream
            self.error_count += 1
            if self.error_count > 3:
                # self.topic.publish(Message=f"Had to retry 3 times\nStatus code = {status_code}\nScraper shutdown time = {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}")
                sys.exit()
            print(f"Hit https error, retry number at {self.retry_connect}")
            time.sleep(30*(2**self.retry_connect))
            return True

        # returning non-False reconnects the stream, with backoff.
