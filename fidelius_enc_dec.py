import os
import uuid
import json
# import subprocess

binPath = "ENC_DEC_fidelius-cli/examples/fidelius-cli-1.2.0/bin/fidelius-cli"

# def execFideliusCli(args):
#     fideliusCommand = [binPath] + args
#     result = subprocess.run(
#         fideliusCommand, stdout=subprocess.PIPE, encoding='UTF-8', shell=True
#     )
#     try:
#         return json.loads(result.stdout)
#     except:
#         print(
#             f'ERROR · execFideliusCli · Command: {" ".join(args)}\n{result.stdout}'
#         )

def getEcdhKeyMaterial():
    # result = execFideliusCli(['gkm'])
    # Can't use subprocess in flask so we will just hard code some encryption value for now
    result = {
        "privateKey": "CZ6Y/f4Ht+C7m3WufYDBa9RIT7ujI7+5FEj7hSiL0w8=",
        "publicKey": "BEUNCQ6gZLmYy06b5FQCcC1CJbDVFSdimVfBssegTH5VDks6MEV35tKHqth87Ov+ipfGRMUC9kwxBQafDVYpUnw=",
        "x509PublicKey": "MIIBMTCB6gYHKoZIzj0CATCB3gIBATArBgcqhkjOPQEBAiB/////////////////////////////////////////7TBEBCAqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqYSRShRAQge0Je0Je0Je0Je0Je0Je0Je0Je0Je0Je0JgtenHcQyGQEQQQqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq0kWiCuGaG4oIa04B7dLHdI0UySPU1+bXxhsinpxaJ+ztPZAiAQAAAAAAAAAAAAAAAAAAAAFN753qL3nNZYEmMaXPXT7QIBCANCAARFDQkOoGS5mMtOm+RUAnAtQiWw1RUnYplXwbLHoEx+VQ5LOjBFd+bSh6rYfOzr/oqXxkTFAvZMMQUGnw1WKVJ8",
        "nonce": "FlV9MfbcOFpifn9vLPeZGVViU61uNi6lqSeWj9r0PcY="
    }
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
    # result = execFideliusCli(['-f', paramsFilePath])
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
    # result = execFideliusCli(['-f', paramsFilePath])
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