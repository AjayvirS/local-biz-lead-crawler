import urllib.parse

base_details = "/Details"
df_view["details"] = df_view["url"].apply(lambda u: f"{base_details}?url={urllib.parse.quote(u, safe='')}")