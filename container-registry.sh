source .env
gitlab_login(){
  echo "Login to docker hub ..."
  docker login
}

register_container() {
  echo -n "Enter your registry:"
  read registry
  echo "Creating docker images ..."
  docker build -t ${registry}/odoo${ODOO_VERSION} ./dockerfiles/odoo/${ODOO_VERSION}
  docker build -t ${registry}/postgres${POSTGRES_VERSION} ./dockerfiles/postgres/${POSTGRES_VERSION}
}

push_container() {
  echo "Pushing docker images to gitlab ..."
  docker push ${registry}/odoo${ODOO_VERSION}
  docker push ${registry}/postgres${POSTGRES_VERSION}
}

gitlab_login
register_container
push_container