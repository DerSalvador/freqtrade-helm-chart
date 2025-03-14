set -x
# Create a directory to store the certificates
mkdir -p ~/docker-certs
cd ~/docker-certs

# Generate the CA private key
openssl genrsa -out ca-key.pem 4096

# Create the CA certificate
openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.crt \
  -subj "/CN=Docker-CA"
# ca-key.pem: The private key of your Certificate Authority.
# ca.crt: The public certificate of your Certificate Authority.
# 2. Generate the Server Key and Certificate Signing Request (CSR)
# This will create a key for your Docker daemon and a request to be signed by the CA.

# bash
# Copy
# Edit
# Generate the server private key
openssl genrsa -out tls.key 4096

# Create a CSR (Certificate Signing Request)
openssl req -subj "/CN=$(hostname)" -new -key tls.key -out server.csr
# tls.key: The private key for the Docker daemon.
# server.csr: The CSR to be signed by the CA.
# 3. Sign the Server Certificate with the CA
# Sign the CSR with your CA to create the server certificate.

# bash
# Copy
# Edit
# Create an extfile to define SAN (Subject Alternative Names)
# echo "subjectAltName = IP:127.0.0.1,IP:$(hostname | awk '{print $1}')" > extfile.cnf
echo "subjectAltName = IP:172.17.48.34" > extfile.cnf

# Sign the server certificate
openssl x509 -req -days 365 -sha256 -in server.csr -CA ca.crt -CAkey ca-key.pem -CAcreateserial \
  -out tls.crt -extfile extfile.cnf
# tls.crt: The signed server certificate.
# extfile.cnf: Specifies the IP addresses Docker will recognize (adjust as needed).
# 4. Verify the Generated Files
# You should now have the following files in your ~/docker-certs directory:

# vbnet
# Copy
# Edit
# ca.crt        # CA Certificate (to verify the server and clients)
# ca-key.pem    # CA Private Key (keep this secure!)
# tls.crt       # Server Certificate (used by Docker daemon)
# tls.key       # Server Private Key (used by Docker daemon)
# 5. Run Docker Daemon with TLS
# Now, you can start the Docker daemon with the following command:

# bash
# Copy
# Edit
# dockerd \
#   --host=tcp://0.0.0.0:2376 \
#   --tlsverify \
#   --tlscacert=~/docker-certs/ca.crt \
#   --tlscert=~/docker-certs/tls.crt \
#   --tlskey=~/docker-certs/tls.key
# 6. (Optional) Create Client Certificates
# If you need mutual TLS (client verification), you can create client certificates as well:

# bash
# Copy
# Edit
# Generate client key
openssl genrsa -out client-key.pem 4096

# Create client CSR
openssl req -subj '/CN=docker-client' -new -key client-key.pem -out client.csr

# Sign client certificate
openssl x509 -req -days 365 -sha256 -in client.csr -CA ca.crt -CAkey ca-key.pem -CAcreateserial \
  -out client-cert.pem -extfile extfile.cnf
# Then, connect to the secured Docker daemon like this:

# bash
# Copy
# Edit
# docker --tlsverify \
#   --tlscacert=~/docker-certs/ca.crt \
#   --tlscert=~/docker-certs/client-cert.pem \
#   --tlskey=~/docker-certs/client-key.pem \
#   -H tcp://<server-ip>:2376 info
