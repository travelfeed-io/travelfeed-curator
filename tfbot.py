import json
import logging
import os
import re
import time
from datetime import timedelta

from bs4 import BeautifulSoup
from langdetect import detect_langs
from markdown import markdown

from beem import Steem
from beem.account import Account
from beem.blockchain import Blockchain
from beem.comment import Comment
from beem.exceptions import ContentDoesNotExistsException
from beem.nodelist import NodeList
from beem.utils import construct_authorperm

whitelist = ['travelfeed',
             'steemitworldmap', 'de-travelfeed', 'cyclefeed', 'tangofever']
curatorlist = ['for91days', 'guchtere', 'mrprofessor',
               'jpphotography', 'elsaenroute', 'smeralda', 'travelfeed', 'worldcapture']
curationaccount = "travelfeed"
# Comment for short posts
shortposttext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/updated-how-to-participate-on-travelfeed-io \n **We require at least 250 words, but your post has only {} words.** \n Thank you very much for your interest and we hope to read some great travel articles from you soon! \n If you believe that you have received this comment by mistake or have updated your post to fit our criteria, you can ignore this comment. For further questions, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Regards, @travelfeed"
# Comment for blacklisted users
blacklisttext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/updated-how-to-participate-on-travelfeed-io \n **You are currently blacklisted from the TravelFeed curation.** \n This is most likely because we have detected plagiarism in one of your posts in the past. If you believe that this is a mistake, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Regards, @travelfeed"
# Comment for other languages
wronglangtext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/updated-how-to-participate-on-travelfeed-io \n We require at least 250 words **in English**. \n Thank you very much for your interest and we hope to read some great travel articles from you soon! \n The language of your post was automatically detected, if your English text is at least 250 words long or you have updated your post to fit our criteria, you can ignore this comment for it to be considered for curation. For further questions, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Regards, @travelfeed"
# Honour text
honourtext = "Congratulations! Your high-quality travel content was selected by @travelfeed curator @{} and earned you a **partial** upvote. We love your hard work and hope to encourage you to continue to publish strong travel-related content. <br> Thank you for being part of the TravelFeed community!"
# Resteem Text
resteemtext = "Congratulations! Your high-quality travel content was selected by @travelfeed curator @{} and earned you a reward, in form of an **upvote** and a **resteem**. Your work really stands out! Your article now has a chance to get featured under the appropriate daily topic on our TravelFeed blog. <br> Thank you for being part of the TravelFeed community!"
# Advote Text
advotetext = "Great read! Your high-quality travel content was selected by @travelfeed curator @{}. We just gave you a small upvote together with over 60 followers of the @travelfeed curation trail. <br> Have you heard of @travelfeed? Using the #travelfeed tag rewards authors and content creators who produce exceptional travel related articles, so be sure use our tag to get much bigger upvotes, resteems and be featured in our curation posts!"
# Manual comment text for short posts
manualshorttext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/updated-how-to-participate-on-travelfeed-io \n **We require at least 250 words.** \n Thank you very much for your interest and we hope to read some great travel articles from you soon! \n If you believe that you have received this comment by mistake or have updated your post to fit our criteria, you can ignore this comment. For further questions, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Regards, @travelfeed"
# Manual comment text for posts that are not in English
manuallangtext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/updated-how-to-participate-on-travelfeed-io \n We require at least 250 words **in English**. \n Thank you very much for your interest and we hope to read some great travel articles from you soon! \n If you believe that you have received this comment by mistake or have updated your post to fit our criteria, you can ignore this comment. For further questions, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Regards, @travelfeed"
# Copyright text
copyrighttext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/updated-how-to-participate-on-travelfeed-io \n We require **proper sourcing** for all media and text that is not your own. \n If you have updated your post with sources, you can ignore this comment. For further questions, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Thank you very much for your interest and we hope to read some great travel articles from you soon! \n Regards, @travelfeed"


logger = logging.getLogger(__name__)
logging.basicConfig(filename='tf.log',
                    format='%(asctime)s %(levelname)s: %(message)s', level=logging.ERROR)
# Log level should be info, but beem throws warnings every few seconds when there is a problem with a node. This cloggs the error files.
nl = NodeList()
nl.update_nodes()
node_list = nl.get_nodes()
stm = Steem(nodes=node_list, timeout=10)
walletpw = os.environ.get('UNLOCK')
stm.wallet.unlock(walletpw)
blockchain = Blockchain(steem_instance=stm)
try:
    account = Account('travelfeed')
    blacklist = account.get_mutings(raw_name_list=True, limit=100)
    logger.error("Got blacklist: "+str(blacklist))
except Exception as error:
    logger.critical('Could not get blacklist: '+repr(error))
    blacklist = []

"""Returns True if *text* contains at least *n* words in the specified *lng* language"""


def is_eligible(text, n, lng):
    for language in detect_langs(text):
        if language.lang == lng:
            probability = language.prob
            word_count = len(text.split(" "))
            if probability * word_count > n:
                return True
            else:
                break
    return False


"""
Beem actions
"""


"""Write a comment if no previous comment is there"""


def write_comment(post, commenttext, isTfio=False):
    time.sleep(3)
    try:
        replies = post.get_all_replies()
        for reply in replies:
            try:
                if reply["author"] == curationaccount:
                    if "Congratulations!" in reply["body"]:
                        logger.critical(
                            "Post already has a comment from @travelfeed!")
                        return
            except:
                continue
    except:
        logger.warning("Problem with analyzing comments of post")
    if (isTfio):
        commenttext += "\n\nThanks for posting through <a href='https://travelfeed.io/'>TravelFeed.io</a>! You have received a larger upvote from us. We hope to see you soon on <a href='https://travelfeed.io/'>TravelFeed.io</a>! \nPosting through <a href='https://travelfeed.io/'>TravelFeed.io</a> also makes your post eligible to participate our <a href='https://travelfeed.io/@travelfeed/blocktrades-anomadsoul-travelfeed-steemfest-ticket-giveaway'>Steemfest ticket giveaway</a>. Please check the post for instructions on how to participate. If you already opted in before September 12th, please double-check that you are opted in since we had some problems with opt-ins not being recorded in the beginning! \nAlso, you can participate in the travel writing contest by <a href='https://travelfeed.io/@invisusmundi'>@invisusmundi</a> where you can earn up to 100 STEEM!"
    else:
        commenttext += "\n\nDid you know that you get larger upvotes when posting through <a href='https://travelfeed.io/'>TravelFeed.io</a>? That is not all, we are also <a href='https://travelfeed.io/@travelfeed/blocktrades-anomadsoul-travelfeed-steemfest-ticket-giveaway'>giving away a ticket to Steemfest</a> to one lucky TravelFeed user. Make sure to read the announcement and opt in! Also, thanks to the travel writing contest by <a href='https://travelfeed.io/@invisusmundi'>@invisusmundi</a> you can now earn up to 100 STEEM on top of the post rewards when posting through our new platform <a href='https://travelfeed.io/'>TravelFeed.io</a>!"
    commenttext += " <a href='https://steempeak.com/contest/@invisusmundi/travelfeed-io-travel-writing-contest-no4'>Read the contest announcement</a> for more information on how to participate. \n\n We are continuously working on improving TravelFeed, recently we <a href='https://travelfeed.io/@travelfeed/easysignup-easylogin'>introduced EasySignUp and EasyLogin, our first step to make TravelFeed ready for mass adoption</a>.\n\n<center> [![](https://ipfs.busy.org/ipfs/QmZhLuw8WE6JMCYHD3EXn3MBa2CSCcygvfFqfXde5z3TLZ)](https://travelfeed.io/@travelfeed/introducing-travelfeed-beta)\n **Learn more about TravelFeed by clicking on the banner above and join our community on [Discord](https://discord.gg/jWWu73H)**.</center>"
    post.reply(commenttext, author=curationaccount,
               meta={'app': "travelfeed/1.3.0"})
    time.sleep(3)
    return


"""Executes curation routine *action* for post *post*"""


def curation_action(action, author, permlink, curator):
    try:
        authorperm = construct_authorperm(author, permlink)
        post = Comment(authorperm)
        app = post.json_metadata.get('app', None).split('/')[0]
        isTfio = app == "travelfeed"
        if post["author"] in blacklist:
            return
        elif action == "curate":
            try:
                if(isTfio):
                    post.upvote(weight=100, voter=curationaccount)
                else:
                    post.upvote(weight=90, voter=curationaccount)
            except Exception as error:
                logger.critical("Could not upvote post "+repr(error))
            try:
                write_comment(post, resteemtext.format(
                    curator), isTfio)
            except Exception as error:
                logger.critical("Could not comment on post "+repr(error))
            try:
                post.resteem(identifier=authorperm, account=curationaccount)
            except Exception as error:
                logger.critical("Could not resteem post "+repr(error))
        elif action == "honour":
            try:
                if(isTfio):
                    post.upvote(weight=65, voter=curationaccount)
                else:
                    post.upvote(weight=50, voter=curationaccount)
            except Exception as error:
                logger.critical("Could not upvote post "+repr(error))
            try:
                write_comment(post, honourtext.format(
                    curator), isTfio)
            except Exception as error:
                logger.critical("Could not comment on post "+repr(error))
        elif action == "short":
            try:
                write_comment(post, manualshorttext.format(
                    author))
            except Exception as error:
                logger.critical("Could not comment on post "+repr(error))
        elif action == "language":
            try:
                write_comment(post, manuallangtext.format(
                    author))
            except Exception as error:
                logger.critical("Could not comment on post "+repr(error))
        elif action == "copyright":
            try:
                write_comment(post, copyrighttext.format(
                    author))
            except Exception as error:
                logger.critical("Could not comment on post "+repr(error))
    except Exception as error:
        logger.critical("Could not execute action for post "+repr(error))
    return


"""Checks post if it fits the criteria"""


def process_post(post):
    commenttext = ""
    if post.time_elapsed() > timedelta(days=1):
        logger.error("Ignoring old post")
        return
    replies = post.get_all_replies()
    for reply in replies:
        if reply["author"] == curationaccount:
            logger.error("Ignoring updated post that already has a comment")
            return
    author = post['author']
    if author in blacklist:
        commenttext = blacklisttext.format(author)
        logger.error("Detected post by blacklisted user @{}".format(author))
    else:
        content = re.sub(r'\w+:\/{2}[\d\w-]+(\.[\d\w-]+)*(?:(?:\/[^\s/]*))*', '', ''.join(
            BeautifulSoup(markdown(post['body']), "html.parser").findAll(text=True)))
        count = len(content.split(" "))
        if count < 240:
            commenttext = shortposttext.format(
                author, count)
            logger.error("Detected short post by @{} who posted with just {} words".format(
                author, count))
        elif is_eligible(content, 225, "en") == False:
            commenttext = wronglangtext.format(
                author)
            logger.error(
                "Detected post by @{} who posted not in English".format(author))
    if not commenttext == "":
        try:
            write_comment(post, commenttext.format(
                author, count))
            logger.error(
                "I sucessfully left a comment for @{}".format(author))
        except:
            logger.critical(
                "There was an error posting the comment.")
        return


"""Steam ops from the Steem Blockchain"""


def stream():
    try:
        blockfile = open('startblock.config', 'r')
        starting_point = int(blockfile.read())
        blockfile.close()
        logger.error("Starting stream from Steem Blockchain...")
    except:
        logger.critical("Could not get start block")
        return
    while True:
        for op in blockchain.stream(start=starting_point, opNames=['comment', 'custom_json']):
            try:
                if op['type'] == 'comment':
                    try:
                        post = Comment(op)
                        post.refresh()
                        if post.is_main_post() and "travelfeed" in post["tags"] and not post.author in whitelist:
                            try:
                                process_post(post)
                            except Exception as err:
                                logger.critical(
                                    "Could not process post: "+repr(err))
                    except ContentDoesNotExistsException:
                        continue
                    except Exception as error:
                        logger.critical(
                            'Problem with comment in stream: '+repr(error))
                        continue
                elif op['type'] == 'custom_json':
                    try:
                        if op['id'] == "travelfeed" and op['required_posting_auths'][0] in curatorlist:
                            payload = json.loads(op['json'])
                            curation_action(
                                payload['action'], payload['author'], payload['permlink'], op['required_posting_auths'][0])
                    except Exception as error:
                        logger.critical(
                            "Error in custom_json stream: "+repr(error))
                        continue
            except Exception as error:
                logger.critical(
                    "Error in stream: "+repr(error))
                continue


if __name__ == '__main__':
    stream()
