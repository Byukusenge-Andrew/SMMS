from apps.integrations.models import SocialMediaAccount
import requests

acc = SocialMediaAccount.objects.filter(platform="facebook").first()
if acc:
    token = acc.access_token
    fields = "id,name,instagram_business_account{id,username,followers_count,name}"
    res = requests.get("https://graph.facebook.com/v18.0/me/accounts", params={"fields": fields, "access_token": token}).json()
    print("ACCOUNTS_AND_INSTA:", res)
