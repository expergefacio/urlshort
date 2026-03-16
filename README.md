# urlshort
Singlefile urlshortener for Flask running in docker
it runs one user whit creds stored in clear text in the env var

````clone the repo
mkdir urlshort
cd urlshort
git clone https://github.com/expergefacio/urlshort.git .````

or in your preferred way
then change the env vars in docker-compose.yml

````nano docker-compose.yml
or
micro docker-compose.yml
or
vim docker-compose.yml````

````    environment:
      #change theese
      SECRET_KEY: "replace-this-with-a-long-random-string"
      ADMIN_USERNAME: "admin"
      ADMIN_PASSWORD: "password"
      PUBLIC_BASE_URL: "https://examlpe.com"````

then your normal
````docker compose up -d````

and bobs your fanny...
