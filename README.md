# travelfeed-curator
TravelFeed curation bot that streams the Steem blockchain and reacts to custom_jsons and comment operations

This python script streams the Steem blockchain for valid custom_json operations by authorised curators (these custom_jsons can be submitted through our dApp) and perform the selected action with the @travelfeed account, e.g. leaving a comment or resteeming, upvoting and commenting on the post.
The script also checks the blockchain stream for posts tagged with "travelfeed" and leaves a comment if they don't meet our criteria (min. 250 words in English).
