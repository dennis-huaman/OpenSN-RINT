# Proyecto del curso de Redes Integradas, basado en estudiar el efecto Doppler en Satélites de órbita LEO utilizando OpenSN
## Preconfiguración
- Sistema Operativo: Ubuntu 24.04 LTS
## Paquetes necesarios
- Docker
- Golang
- NodeJS
## Despliegue inicial
git clone https://github.com/OpenSN-Library/OpenSN-Library.git
# git clone https://github.com/dennis-huaman/OpenSN-RINT.git (mi repo/verificar si funciona igual)
cd OpenSN-Library/
make build
## Configuración de parámetros del kernel
sudo tee -a /etc/sysctl.conf <<EOF
fs.inotify.max_user_instances = 4096
net.ipv4.neigh.default.gc_thresh1 = 8192
net.ipv4.neigh.default.gc_thresh2 = 16384
net.ipv4.neigh.default.gc_thresh3 = 32768
EOF
## Despliegue
cd ~/Escritorio/OpenSN-Library/daemon
make dep
cd ~/Escritorio/OpenSN-Library/opensn_build
cd opensn-daemon
sudo ./NodeDaemon
