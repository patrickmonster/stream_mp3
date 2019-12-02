import os
class CheapMP3:
    BITRATES_MPEG1_L3 = [
        0,  32,  40,  48,  56,  64,  80,  96,
        112, 128, 160, 192, 224, 256, 320,  0 ]
    BITRATES_MPEG2_L3 = [
        0,   8,  16,  24,  32,  40,  48,  56,
        64,  80,  96, 112, 128, 144, 160, 0 ]
    SAMPLERATES_MPEG1_L3 = [44100, 48000, 32000, 0 ]
    SAMPLERATES_MPEG2_L3 = [22050, 24000, 16000, 0]

    hash_255 = None

    def __init__(self,inputFile):
        self.fname = inputFile
        self.hash_255 = [i for i in range(128)]
        self.hash_255.extend([i for i in range(-128,0)])


    def WriteFile(self,outputFile, numFrames, startFrame = 0):
        maxFrameLen = 0
        for i in range(numFrames):
            if (self.mFrameLens[startFrame + i] > maxFrameLen):
                maxFrameLen = self.mFrameLens[startFrame + i]
        pos = 0
        with open(self.fname,'rb') as inf:
            with open(outputFile,'wb') as ouf:
                for i in range(numFrames):
                    skip = self.mFrameOffsets[startFrame + i] - pos
                    length = self.mFrameLens[startFrame + i]
                    if (skip > 0) :
                        inf.seek(skip,1)
                        pos += skip
                    ouf.write(inf.read(length))
                    pos += length

    def convert_byte_to_char(self,b):
        if type(b) == int:
            return self.hash_255[b]
        else:
            return int.from_bytes(b, byteorder='little', signed=True)

    def ReadFile(self):
        self.mNumFrames = 0
        self.mMaxFrames = 64  # This will grow as needed
        self.mFrameOffsets = [0 for _ in range(self.mMaxFrames)]
        self.mFrameLens = [0 for _ in range(self.mMaxFrames)]
        self.mFrameGains = [0 for _ in range(self.mMaxFrames)]
        self.mBitrateSum = 0
        self.mMinGain = 255
        self.mMaxGain = 0

        self.mFileSize = os.path.getsize(self.fname)

        self.debug = True

        with open(self.fname,'rb') as stream:
            pos = offset = 0
            buffer = bytearray()
            while pos < self.mFileSize - 12:
                while offset < 12:
                    tmp = stream.read(12 - offset)
                    buffer.extend(tmp)
                    offset += len(tmp)
                bufferOffset = 0
                while bufferOffset < 12 and self.convert_byte_to_char(buffer[bufferOffset]) != -1:
                    bufferOffset +=1
                
                if bufferOffset > 0:
                    pos += bufferOffset
                    offset = 12 - bufferOffset
                    if offset > 0:
                        buffer = buffer[bufferOffset:]
                    else :
                        buffer = bytearray()
                    if offset >= 0:
                        continue
                    break
                mpgVersion  = 0
                bf1 = self.convert_byte_to_char(buffer[1])
                if bf1 == -6 or bf1 == -5:
                    mpgVersion = 1
                elif bf1 == -14 or bf1 == -13:
                    mpgVersion = 2
                else :
                    bufferOffset = 1
                    for i in range(12-bufferOffset):
                        buffer[i] = buffer[bufferOffset + i]
                    pos += bufferOffset
                    offset = 12 - bufferOffset
                    continue
                bitRate = sampleRate = 0
                bf2 = self.convert_byte_to_char(buffer[2])
                if (mpgVersion == 1) :
                    # MPEG 1 Layer III
                    bitRate = self.BITRATES_MPEG1_L3[(bf2 & -16) >> 4]
                    sampleRate = self.SAMPLERATES_MPEG1_L3[(bf2 & 12) >> 2]
                else:
                    # MPEG 2 Layer III
                    bitRate = self.BITRATES_MPEG2_L3[(bf2 & -16) >> 4]
                    sampleRate = self.SAMPLERATES_MPEG2_L3[(bf2 & 12) >> 2]

                if (bitRate == 0 or sampleRate == 0):
                    bufferOffset = 2
                    #for (int i = 0; i < 12 - bufferOffset; i++):
                    for i in range(12 - bufferOffset):
                        buffer[i] = buffer[bufferOffset + i]
                    pos += bufferOffset
                    offset = 12 - bufferOffset
                    continue

                self.mGlobalSampleRate = sampleRate
                padding = (bf2 & 2) >> 1
                frameLen = int(144 * bitRate * 1000 / sampleRate + padding)

                gain = 0
                bf3 = self.convert_byte_to_char(buffer[3])
                bf9 = self.convert_byte_to_char(buffer[9])
                bf10 = self.convert_byte_to_char(buffer[10])
                if ((bf3 & -64) == -64) :
                    # 1 channel
                    self.mGlobalChannels = 1
                    if (mpgVersion == 1) :
                        gain = ((bf10 & 1) << 7) + ((self.convert_byte_to_char(buffer[11]) & -2) >> 1)
                    else :
                        gain = ((bf9 & 3) << 6) +((bf10 & -4) >> 2)
                else :
                    # 2 channels
                    self.mGlobalChannels = 2
                    if (mpgVersion == 1) :
                        gain = ((bf9  & 127) << 1) +((bf10 & -128) >> 7)
                    else:
                        gain = 0  # ???
                    

                self.mBitrateSum += bitRate 

                self.mFrameOffsets[self.mNumFrames] = pos
                self.mFrameLens[self.mNumFrames] = frameLen
                self.mFrameGains[self.mNumFrames] = gain
                if (gain < self.mMinGain):
                    self.mMinGain = gain
                if (gain > self.mMaxGain):
                    self.mMaxGain = gain

                self.mNumFrames+=1
                if (self.mNumFrames == self.mMaxFrames) :
                    # We need to grow our arrays.  Rather than naively
                    # doubling the array each time, we estimate the exact
                    # number of frames we need and add 10% padding.  In
                    # practice this seems to work quite well, only one
                    # resize is ever needed, however to avoid pathological
                    # cases we make sure to always double the size at a minimum.

                    self.mAvgBitRate = self.mBitrateSum / self.mNumFrames
                    totalFramesGuess =((self.mFileSize / self.mAvgBitRate) * sampleRate) / 144000
                    newMaxFrames = int(totalFramesGuess * 11 / 10)
                    if (newMaxFrames < self.mMaxFrames * 2):
                        newMaxFrames = self.mMaxFrames * 2

                    newOffsets = [0 for _ in range(newMaxFrames)]
                    newLens = [0 for _ in range(newMaxFrames)]
                    newGains = [0 for _ in range(newMaxFrames)]
                    for i in range(self.mNumFrames):
                        newOffsets[i] = self.mFrameOffsets[i]
                        newLens[i] = self.mFrameLens[i]
                        newGains[i] = self.mFrameGains[i]

                    self.mFrameOffsets = newOffsets
                    self.mFrameLens = newLens
                    self.mFrameGains = newGains
                    self.mMaxFrames = newMaxFrames
                
                stream.seek(frameLen - 12, 1) # 현 위치부터
                pos += frameLen
                offset = 0
                buffer = bytearray()
            # We're done reading the file, do some postprocessing
            
            if (self.mNumFrames > 0):
                self.mAvgBitRate = self.mBitrateSum / self.mNumFrames
            else:
                self.mAvgBitRate = 0
        #open
mp3 = CheapMP3("test.mp3")
mp3.ReadFile()
print(mp3.mFrameOffsets, len(mp3.mFrameOffsets))
#mp3.WriteFile("test2.mp3",800,1000)
