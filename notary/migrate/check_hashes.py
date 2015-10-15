import json
import sys
import urllib.request
import subprocess
from xml.dom import minidom

def getChildNodes(x):
    return [a for a in x[0].childNodes if not a.nodeName=='#text']

#assuming both events happened on the same day, get the time
#difference between them in seconds
#the time string looks like "2015-04-15T19:00:59.000Z"
def getSecondsDelta (later, sooner):
    assert (len(later) == 24)
    if (later[:11] != sooner[:11]):
        return 999999; #not on the same day
    laterTime = later[11:19].split(':')
    soonerTime = sooner[11:19].split(':')
    laterSecs = int(laterTime[0])*3600+int(laterTime[1])*60+int(laterTime[2])
    soonerSecs = int(soonerTime[0])*3600+int(soonerTime[1])*60+int(soonerTime[2])
    return laterSecs - soonerSecs

j = json.loads(open('/dev/shm/notary/migrate/migrate.json').read())

if j[1]['previous notary oracle']['first sha256 checksum'] != sys.argv[1] or \
   j[1]['previous notary oracle']['second sha256 checksum'] != sys.argv[2] or \
   j[1]['previous signing oracle']['first sha256 checksum'] != sys.argv[3] or \
   j[1]['previous signing oracle']['second sha256 checksum'] != sys.argv[4]:
    with open('/tmp/argv', 'w') as f: f.write(str(sys.argv))
    exit(11)

#Ask Amazon what my instance id is
myInstanceId = urllib.request.urlopen('http://169.254.169.254/latest/meta-data/instance-id').read().decode()
#as an extra check, get my internal IP address and MAC address
 
o = subprocess.check_output(['ifconfig', 'eth0'])
myMacAddress = o.split()[4].decode()
myInternalIP = o.split()[6].decode().split(':')[1]

DIURL  = j[1]['new oracles Query API URLs']['DescribeInstances']
DVURL = j[1]['new oracles Query API URLs']['DescribeVolumes']

data = urllib.request.urlopen(DIURL).read().decode()
xmlDoc = minidom.parseString(data)
rs = xmlDoc.getElementsByTagName('reservationSet')
instanceFound = False
for item in getChildNodes(rs):
    instance = getChildNodes(item.getElementsByTagName('instancesSet'))[0]
    instanceId = instance.getElementsByTagName('instanceId')[0].firstChild.data
    if instanceId == myInstanceId:
        instanceFound = True
        break
if not instanceFound:
    exit(12)

ni = getChildNodes(instance.getElementsByTagName('networkInterfaceSet'))[0]
macAddress = ni.getElementsByTagName('macAddress')[0].firstChild.data
if myMacAddress != macAddress: exit(13)

privateIpAddress = ni.getElementsByTagName('privateIpAddress')[0].firstChild.data
if myInternalIP != privateIpAddress: exit(14)

#there should be 3 volumes which were attached no later than 3 after seconds this instance was started
launchTime = instance.getElementsByTagName('launchTime')[0].firstChild.data

root_volume_id = None
notary_volume_id = None
signing_volume_id = None
notary_volume_attach_time = None
signing_volume_attach_time = None

bdm = getChildNodes(instance.getElementsByTagName('blockDeviceMapping'))
if len(bdm) != 3:
    exit(15)

for volume in bdm:
    deviceName = volume.getElementsByTagName('deviceName')[0].firstChild.data
    volume_id = volume.getElementsByTagName('volumeId')[0].firstChild.data
    attachTime = volume.getElementsByTagName('attachTime')[0].firstChild.data
    if getSecondsDelta(attachTime, launchTime) > 5:
        exit(16)
    if deviceName == '/dev/xvda':
        root_volume_id = volume_id
    elif deviceName == '/dev/xvdj':
        notary_volume_id = volume_id
        notary_volume_attach_time = attachTime
    elif  deviceName == '/dev/xvdk':
        signing_volume_id = volume_id
        signing_volume_attach_time = attachTime
    else:
        exit(17)

if not (root_volume_id and notary_volume_id and signing_volume_id):
    exit(18)

#make sure that the oracle server volumes were created from correct snapshots 
#and they were attached the same instant they were created
data = urllib.request.urlopen(DVURL).read().decode()
xmlDoc = minidom.parseString(data)
vs = getChildNodes(xmlDoc.getElementsByTagName('volumeSet'))
notary_snapshot_id =  j[1]['previous notary oracle']['snapshot id'] 
signing_snapshot_id = j[1]['previous signing oracle']['snapshot id'] 

notary_volume_checked = False
signing_volume_checked = False
for volume in vs:
    volumeId = volume.getElementsByTagName('volumeId')[0].firstChild.data
    snapshotId = volume.getElementsByTagName('snapshotId')[0].firstChild.data
    createTime = volume.getElementsByTagName('createTime')[0].firstChild.data
    if volumeId == notary_volume_id:
        if not ((snapshotId == notary_snapshot_id) and (getSecondsDelta(createTime, notary_volume_attach_time) == 0)):
            exit(19)
        notary_volume_checked = True
    elif volumeId == signing_volume_id:
        if not ((snapshotId == signing_snapshot_id) and (getSecondsDelta(createTime, signing_volume_attach_time) == 0)):
            exit(20)
        signing_volume_checked = True

if not (notary_volume_checked and signing_volume_checked):
    exit(21)

#exit with success code
exit(123)
    




