from beem import Steem
from beem.blockchain import Blockchain
from beem.comment import Comment
from beem.account import Account
from beem.nodelist import NodeList
from beem.exceptions import ContentDoesNotExistsException
from beem.utils import construct_authorperm
from langdetect import detect_langs
from datetime import timedelta
from bs4 import BeautifulSoup
from markdown import markdown
import logging
import json
import os
import re

whitelist = ['travelfeed',
             'steemitworldmap', 'de-travelfeed', 'cyclefeed']
curatorlist = ['for91days', 'guchtere', 'mrprofessor',
               'jpphotography', 'elsaenroute', 'smeralda']
curationaccount = "travelfeed"
# Comment for short posts
shortposttext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/how-to-participate-use-travelfeed-in-your-posts \n **We require at least 250 words, but your post has only {} words.** \n Thank you very much for your interest and we hope to read some great travel articles from you soon! \n If you believe that you have received this comment by mistake or have updated your post to fit our criteria, you can ignore this comment. For further questions, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Regards, @travelfeed"
# Comment for blacklisted users
blacklisttext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/how-to-participate-use-travelfeed-in-your-posts \n **You are currently blacklisted from the TravelFeed curation.** \n This is most likely because we have detected plagiarism in one of your posts in the past. If you believe that this is a mistake, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Regards, @travelfeed"
# Comment for other languages
wronglangtext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/how-to-participate-use-travelfeed-in-your-posts \n We require at least 250 words **in English**. \n Thank you very much for your interest and we hope to read some great travel articles from you soon! \n The language of your post was automatically detected, if your English text is at least 250 words long or you have updated your post to fit our criteria, you can ignore this comment for it to be considered for curation. For further questions, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Regards, @travelfeed"
# Honour text
honourtext = "Congratulations! Your high-quality travel content was selected by @travelfeed curator @{} and earned you a **partial** upvote. We love your hard work and hope to encourage you to continue to publish strong travel-related content. <br> Thank you for being part of the TravelFeed community! <center> [![TravelFeed](https://ipfs.busy.org/ipfs/QmZhLuw8WE6JMCYHD3EXn3MBa2CSCcygvfFqfXde5z3TLZ)](https://travelfeed.io/@travelfeed/introducing-travelfeed-featuring-steemit-s-best-travel-content) <br> **Learn more about our travel project by clicking on the banner above and join our community on [Discord](https://discord.gg/jWWu73H)**.</center>"
# Resteem Text
resteemtext = "Congratulations! Your high-quality travel content was selected by @travelfeed curator @{} and earned you a reward, in form of a **100% upvote** and a **resteem**. Your work really stands out! Your article now has a chance to get featured under the appropriate daily topic on our TravelFeed blog. <br> Thank you for being part of the TravelFeed community! <br> <center>[![TravelFeed](https://ipfs.busy.org/ipfs/QmNTkoKQNzuQbQGbcZ1exTMjvxYUprdnVczxnvib9VUSqB)](http://travelfeed.io/travelfeed/@travelfeed/introducing-travelfeed-featuring-steemit-s-best-travel-content) <br> **Learn more about our travel project by clicking on the banner above and join our community on [Discord](https://discord.gg/jWWu73H)**</center>"
# Advote Text
advotetext = "Great read! Your high-quality travel content was selected by @travelfeed curator @{}. We just gave you a small upvote together with over 60 followers of the @travelfeed curation trail. <br> Have you heard of @travelfeed? Using the #travelfeed tag rewards authors and content creators who produce exceptional travel related articles, so be sure use our tag to get much bigger upvotes, resteems and be featured in our curation posts! <br> <center>[![TravelFeed](https://ipfs.busy.org/ipfs/QmNTkoKQNzuQbQGbcZ1exTMjvxYUprdnVczxnvib9VUSqB)](http://travelfeed.io/travelfeed/@travelfeed/introducing-travelfeed-featuring-steemit-s-best-travel-content) <br> **Learn more about our travel project by clicking on the banner above and join our community on [Discord](https://discord.gg/jWWu73H)**</center>"
# Manual comment text for short posts
manualshorttext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/how-to-participate-use-travelfeed-in-your-posts \n **We require at least 250 words.** \n Thank you very much for your interest and we hope to read some great travel articles from you soon! \n If you believe that you have received this comment by mistake or have updated your post to fit our criteria, you can ignore this comment. For further questions, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Regards, @travelfeed"
# Manual comment text for posts that are not in English
manuallangtext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/how-to-participate-use-travelfeed-in-your-posts \n We require at least 250 words **in English**. \n Thank you very much for your interest and we hope to read some great travel articles from you soon! \n If you believe that you have received this comment by mistake or have updated your post to fit our criteria, you can ignore this comment. For further questions, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Regards, @travelfeed"
# Copyright text
copyrighttext = "Hi @{}, \n Thank you for participating in the #travelfeed curated tag. To maintain a level of quality on the project we have certain criteria that must be met for participation. Please review the following: https://travelfeed.io/@travelfeed/how-to-participate-use-travelfeed-in-your-posts \n We require **proper sourcing** for all media and text that is not your own. \n If you have updated your post with sources, you can ignore this comment. For further questions, please contact us on the [TravelFeed Discord](https://discord.gg/jWWu73H). \n Thank you very much for your interest and we hope to read some great travel articles from you soon! \n Regards, @travelfeed"


logger = logging.getLogger(__name__)
logging.basicConfig(filename='tf.log',
                    format='%(asctime)s %(levelname)s: %(message)s', level=logging.ERROR)
# Log level should be info, but beem throws warnings every few seconds when there is a problem with a node. This cloggs the error files.
nl = NodeList()
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


def write_comment(post, commenttext):
    replies = post.get_all_replies()
    for reply in replies:
        if reply["author"] == curationaccount:
            if "Congratulations!" in reply["body"]:
                logger.critical(
                    "Post already has a comment from @travelfeed!")
                return
    post.reply(commenttext, author=curationaccount,
               meta={'app': "travelfeed/0.2.5"})
    return


"""Executes curation routine *action* for post *post*"""


def curation_action(action, author, permlink, curator):
    try:
        authorperm = construct_authorperm(author, permlink)
        post = Comment(authorperm)
        if post["author"] in blacklist:
            return
        elif action == "curate":
            try:
                post.upvote(weight=100, voter=curationaccount)
            except Exception as error:
                logger.critical("Could not upvote post "+repr(error))
            try:
                write_comment(post, resteemtext.format(
                    curator))
            except Exception as error:
                logger.critical("Could not comment on post "+repr(error))
            try:
                post.resteem(identifier=authorperm, account=curationaccount)
            except Exception as error:
                logger.critical("Could not resteem post "+repr(error))
        elif action == "honour":
            try:
                post.upvote(weight=50, voter=curationaccount)
            except Exception as error:
                logger.critical("Could not upvote post "+repr(error))
            try:
                write_comment(post, honourtext.format(
                    curator))
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
                write_comment(post, copyrighttext)
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
