import os
import uuid
import json
import sys
import pyperclip
import subprocess

from utils import getFideliusVersion

fideliusVersion = getFideliusVersion()
dirname = os.path.dirname(os.path.abspath(__file__))
binPath = r"F:\AbPt_ABDM\Extras\ENC_DEC_fidelius-cli\examples\fidelius-cli-1.2.0\bin\fidelius-cli"
# os.path.join(
#     dirname, f'../fidelius-cli-{fideliusVersion}/bin/fidelius-cli'
# )

def execFideliusCli(args):
    fideliusCommand = [binPath] + args
    result = subprocess.run(
        fideliusCommand, stdout=subprocess.PIPE, encoding='UTF-8', shell=True
    )
    try:
        return json.loads(result.stdout)
    except:
        print(
            f'ERROR · execFideliusCli · Command: {" ".join(args)}\n{result.stdout}'
        )


def getEcdhKeyMaterial():
    result = execFideliusCli(['gkm'])
    return result


def writeParamsToFile(*params):
    fileContents = '\n'.join(params)
    filePath = os.path.join(dirname, 'output_params', f'{str(uuid.uuid4())}.txt')
    os.makedirs(os.path.dirname(filePath), exist_ok=True)
    f = open(filePath, 'a')
    f.write(fileContents)
    f.close()
    return filePath


def removeFileAtPath(filePath):
    os.remove(filePath)


def encryptData(encryptParams):
    paramsFilePath = writeParamsToFile(
        'e',
        encryptParams['stringToEncrypt'],
        encryptParams['senderNonce'],
        encryptParams['requesterNonce'],
        encryptParams['senderPrivateKey'],
        encryptParams['requesterPublicKey']
    )
    result = execFideliusCli(['-f', paramsFilePath])
    removeFileAtPath(paramsFilePath)
    return result


def decryptData(decryptParams):
    paramsFilePath = writeParamsToFile(
        'd',
        decryptParams['encryptedData'],
        decryptParams['requesterNonce'],
        decryptParams['senderNonce'],
        decryptParams['requesterPrivateKey'],
        decryptParams['senderPublicKey']
    )
    result = execFideliusCli(['-f', paramsFilePath])
    removeFileAtPath(paramsFilePath)
    return result


def runExample(stringToEncrypt):
    requesterKeyMaterial = getEcdhKeyMaterial()
    senderKeyMaterial = getEcdhKeyMaterial()

    print(json.dumps({
        'requesterKeyMaterial': requesterKeyMaterial,
        'senderKeyMaterial': senderKeyMaterial
    }, indent=4))

    encryptionResult = encryptData({
        'stringToEncrypt': stringToEncrypt,
        'senderNonce': senderKeyMaterial['nonce'],
        'requesterNonce': requesterKeyMaterial['nonce'],
        'senderPrivateKey': senderKeyMaterial['privateKey'],
        'requesterPublicKey': requesterKeyMaterial['publicKey']
    })

    encryptionWithX509PublicKeyResult = encryptData({
        'stringToEncrypt': stringToEncrypt,
        'senderNonce': senderKeyMaterial['nonce'],
        'requesterNonce': requesterKeyMaterial['nonce'],
        'senderPrivateKey': senderKeyMaterial['privateKey'],
        'requesterPublicKey': requesterKeyMaterial['x509PublicKey']
    })

    # print(json.dumps({
    #     'encryptedData': encryptionResult['encryptedData'],
    #     'encryptedDataWithX509PublicKey': encryptionWithX509PublicKeyResult['encryptedData']
    # }, indent=4))

    decryptionResult = decryptData({
        'encryptedData': encryptionResult['encryptedData'],
        'requesterNonce': requesterKeyMaterial['nonce'],
        'senderNonce': senderKeyMaterial['nonce'],
        'requesterPrivateKey': requesterKeyMaterial['privateKey'],
        'senderPublicKey': senderKeyMaterial['publicKey']
    })

    decryptionResultWithX509PublicKey = decryptData({
        'encryptedData': encryptionResult['encryptedData'],
        'requesterNonce': requesterKeyMaterial['nonce'],
        'senderNonce': senderKeyMaterial['nonce'],
        'requesterPrivateKey': requesterKeyMaterial['privateKey'],
        'senderPublicKey': senderKeyMaterial['x509PublicKey']
    })

    # print(json.dumps({
    #     'decryptedData': decryptionResult['decryptedData'],
    #     'decryptedDataWithX509PublicKey': decryptionResultWithX509PublicKey['decryptedData']
    # }, indent=4))

# def runExample(stringToEncrypt):
#     requesterKeyMaterial = getEcdhKeyMaterial()
#     senderKeyMaterial = getEcdhKeyMaterial()

#     print(json.dumps({
#         'requesterKeyMaterial': requesterKeyMaterial,
#         'senderKeyMaterial': senderKeyMaterial
#     }, indent=4))

#     encryptionResult = encryptData({
#         'stringToEncrypt': stringToEncrypt,
#         'senderNonce': senderKeyMaterial['nonce'],
#         'requesterNonce': requesterKeyMaterial['nonce'],
#         'senderPrivateKey': senderKeyMaterial['privateKey'],
#         'requesterPublicKey': requesterKeyMaterial['publicKey']
#     })

#     encryptionWithX509PublicKeyResult = encryptData({
#         'stringToEncrypt': stringToEncrypt,
#         'senderNonce': senderKeyMaterial['nonce'],
#         'requesterNonce': requesterKeyMaterial['nonce'],
#         'senderPrivateKey': senderKeyMaterial['privateKey'],
#         'requesterPublicKey': requesterKeyMaterial['x509PublicKey']
#     })

#     print(json.dumps({
#         'encryptedData': encryptionResult['encryptedData'],
#         'encryptedDataWithX509PublicKey': encryptionWithX509PublicKeyResult['encryptedData']
#     }, indent=4))

#     decryptionResult = decryptData({
#         'encryptedData': encryptionResult['encryptedData'],
#         'requesterNonce': requesterKeyMaterial['nonce'],
#         'senderNonce': senderKeyMaterial['nonce'],
#         'requesterPrivateKey': requesterKeyMaterial['privateKey'],
#         'senderPublicKey': senderKeyMaterial['publicKey']
#     })

#     decryptionResultWithX509PublicKey = decryptData({
#         'encryptedData': encryptionResult['encryptedData'],
#         'requesterNonce': requesterKeyMaterial['nonce'],
#         'senderNonce': senderKeyMaterial['nonce'],
#         'requesterPrivateKey': requesterKeyMaterial['privateKey'],
#         'senderPublicKey': senderKeyMaterial['x509PublicKey']
#     })

#     print(json.dumps({
#         'decryptedData': decryptionResult['decryptedData'],
#         'decryptedDataWithX509PublicKey': decryptionResultWithX509PublicKey['decryptedData']
#     }, indent=4))

def runExample1(stringToEncrypt, requesterKeyMaterial):
    senderKeyMaterial = getEcdhKeyMaterial()

    print(senderKeyMaterial)

    encryptionResult = encryptData({
        'stringToEncrypt': stringToEncrypt,
        'senderNonce': senderKeyMaterial['nonce'],
        'requesterNonce': requesterKeyMaterial['nonce'],
        'senderPrivateKey': senderKeyMaterial['privateKey'],
        'requesterPublicKey': requesterKeyMaterial['publicKey']
    })
    
    pyperclip.copy(encryptionResult['encryptedData'])

# def main(stringToEncrypt='{"data": "There is no war in Ba Sing Se!"}'):
#     runExample(stringToEncrypt)

def main(filePath, nnce=None, pubKey=None):

    # Open JSON file path and read data from it
    f = open(filePath)
    data = json.load(f)
    f.close()
    strData = json.dumps(data)

    # create dictionary to pass outside pub key and nonce
    outsidePubKeyMaterial = {
        'nonce': nnce,
        'publicKey': pubKey
    }

    runExample1(strData, outsidePubKeyMaterial)

if __name__ == '__main__':
    arg_list = sys.argv

    # arg_list[0] is the file that is run
    json_fp = arg_list[1]
    nonce_val = arg_list[2]
    pub_key = arg_list[3]
    
    main(json_fp, nonce_val, pub_key)
