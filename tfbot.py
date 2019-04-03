from beem import Steem
from beem.blockchain import Blockchain
from beem.comment import Comment
from beem.nodelist import NodeList
from beem.exceptions import ContentDoesNotExistsException
from langdetect import detect_langs
import logging

whitelist = ['travelfeed', 'tangofever',
             'steemitworldmap', 'de-travelfeed', 'cyclefeed']
blacklist = []
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
logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)
nl = NodeList()
weights = {'block': 1, 'history': 0, 'apicall': 1, 'config': 0}
node_list = nl.update_nodes(weights)
stm = Steem(nodes=node_list)
blockchain = Blockchain(steem_instance=stm)
processed_posts = []


def is_eligible(text, n, lng):
    """Returns True if *text* contains at least *n* words in the specified *lng* language"""
    for language in detect_langs(text):
        if language.lang == lng:
            probability = language.prob
            word_count = len(text.split(" "))
            if probability * word_count > n:
                return True
            else:
                break
    return False


def write_comment(post, commenttext, count):
    replies = post.get_all_replies()
    for reply in replies:
        if reply["author"] == "travelfeed":
            if "Congratulations!" in reply["body"]:
                console.warning(
                    "Post already has a comment from @travelfeed!")
                return
    post.reply(commenttext.format(
        author, count), author=curationaccount)
    return


def process_post(post):
    """Checks for each *post* in #travelfeed if it fits the criteria"""
    commenttext = ""
    # If a post is edited within the first two minutes it would be processed twice without checking for the second condition. The array of processed posts does not need to be saved at exit since it is only relevant for two minutes
    if post.time_elapsed() > timedelta(minutes=2) or post in processed_posts:
        logger.info("Ignoring updated post")
        return
    elif author in blacklist:
        commenttext = blacklisttext
        logger.info("Detected post by blacklisted user @{}".format(author))
        return
    else:
        content = re.sub(r'\w+:\/{2}[\d\w-]+(\.[\d\w-]+)*(?:(?:\/[^\s/]*))*', '', ''.join(
            BeautifulSoup(markdown(body), "html.parser").findAll(text=True)))
        count = len(content.split(" "))
        check_eligible = is_eligible(content, 225, "en")
        if count < 240:
            commenttext = shortposttext
            logger.info("Detected short post by @{} who posted with just {} words".format(
                author, count))
        elif check_eligible == False:
            commenttext = wronglangtext
            logger.info(
                "Detected post by @{} who posted not in English".format(author))
        if not commenttext == "":
            try:
                write_comment(post, commenttext.format(
                    author, count))
                logger.info(
                    "I sucessfully left a comment for @{}".format(author))
            except:
                logger.warning(
                    "There was an error posting the comment.")
                return
        processed_posts += [authorperm]
        return


def stream():
    """Steam ops from the Steem Blockchain"""
    logger.info("Started stream from Steem Blockchain")
    while True:
        for op in blockchain.stream(opNames=['comment', 'custom_json']):
            try:
                if op['type'] == 'comment':
                    try:
                        post = Comment(op)
                        post.refresh()
                        if post.is_main_post() and "travelfeed" in post["tags"] and not post.author in whitelist:
                            try:
                                process_post()
                            except Exception as err:
                                console.warning(
                                    "Could not process post: "+repr(err))
                    except ContentDoesNotExistsException:
                        continue
                    except Exception as error:
                        logger.warning(
                            'Problem with comment in stream: '+repr(error))
                        continue
                # elif op['type'] == 'transfer':
                #     try:
                #         process_transfer()
                #     except Exception as error:
                #         logger.warning(
                #             "Warning in transfer stream: "+repr(error))
                #         continue
            except Exception as error:
                logger.warning(
                    "Warning in stream: "+repr(error))
                continue


if __name__ == '__main__':
    stream()
