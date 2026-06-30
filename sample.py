from gmail import authenticate

accounts = {
    "personal": "accounts/personal/token.json",
    "college": "accounts/college/token.json",
    "iitm": "accounts/IITM/token.json"
}

for name, path in accounts.items():
    service = authenticate(path)
    labels = service.users().labels().list(userId="me").execute()
    for label in labels["labels"]:
        if "cortexmail" in label["name"].lower():
            print(f"{name}: {label['name']} -> {label['id']}")