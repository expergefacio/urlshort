# urlshort
Singlefile urlshortener for Flask running in docker  
it runs one user whit creds stored in clear text in the env var

it runs auto inc on base64-url, so you get about 4163 on the first one and two bytes  
ie. `example.com/A` and `exmaple.com/_z`  
also supports `example.com/custom`

# howto
## Clone the repo
````
mkdir urlshort
cd urlshort
git clone https://github.com/expergefacio/urlshort.git .
rm LICENSE
rm README.md
````
or in your preferred way

## change the env vars in docker-compose.yml
````
nano docker-compose.yml
#or
micro docker-compose.yml
#or
vim docker-compose.yml
````
## then
````
    environment:
      #change theese
      SECRET_KEY: "replace-this-with-a-long-random-string"
      ADMIN_USERNAME: "admin"
      ADMIN_PASSWORD: "password"
      PUBLIC_BASE_URL: "https://examlpe.com/"
````

## then your normal
````
docker compose up -d
````

## Admin
https://examlpe.com/manage

and bobs your fanny 🤘🤓🤘
