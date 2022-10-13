import os
import uuid
import json
import subprocess

binPath = "ENC_DEC_fidelius-cli/examples/fidelius-cli-1.2.0/bin/fidelius-cli"

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
    filePath = os.path.join(os.getcwd(), 'output_params', f'{str(uuid.uuid4())}.txt')
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
    
    return {
        "content": encryptionResult['encryptedData'],
        "senderPubKeyVal": senderKeyMaterial['publicKey'],
        "senderNonceVal": senderKeyMaterial['nonce']
    }