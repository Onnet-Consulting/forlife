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
}

push_container() {
  echo "Pushing docker images to gitlab ..."
  docker push ${registry}/odoo${ODOO_VERSION}
}

gitlab_login
register_container
push_container