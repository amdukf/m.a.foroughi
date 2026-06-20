Execute this before docker compose up -d
```
mkdir _timetagger
chown 1000:1000 _timetagger
```

Generate `TIMETAGGER_CREDENTIALS` with this command:

```
python3 -c 'import bcrypt,json;print(json.dumps({"user":bcrypt.hashpw(b"password",bcrypt.gensalt()).decode()}))'
```

and escape the $, like the example in compose.yml file


NOTE:
If you dont have internet, you can load the timetagger image that exists in this repo:
```
docker load < time.tar
```
