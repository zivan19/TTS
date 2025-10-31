"""Simplified synthesis pipeline used by the FastAPI demo server."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from ..jobs import JobManager


# Base64-encoded 1 second 440 Hz tone generated during development time so the
# repository does not need to ship binary fixtures. The dummy synthesizer decodes
# it once when instantiated.
_PLACEHOLDER_MP3_BASE64 = """
//OAxAAoaLJcA1pIARmRImTJmVKmXLmXKmRFoRhYIY4caVSbeKdO+efWevGdeSbdOZcSDgaABQRI
RCQiooIsRrj8BsLgHAGBsEw2TtwUQCgkQIIOjh4f/4CPw//wH//Qwz/AA9/5hgB/AAPP8PDAAyAA
B4eHh4YAAAAAB4eHh4YAAAAIDw8PD0gAI+QPH/+Bn/4eHh4eGAAAAAAeHh4eGAAAACA8PDw9IAAA
j2w8emRFIMMGBAGBAKLhkbi0WioB6ZEEwSCgob3IMfCImHBkjv/zgsQhJptynZ+caAYxoEDGBQML
SpbhnMSLCgFiANEAq/gZQCKAK34W0FpBWRPv8RoLsO0YUS3/xPgvQWodojIjJJf/5eJIxLpdSLxe
R///LpImReLxiXS6kXklo////5dMi8XkS6ipJJaLUv///9v6KsxVMkUTFJIkjEukiZF4kv/1WqW1
FZarKYAUADgQAFEACgYGeB1GB2iYhg5YdIYeSDAGFsjfRlBpEYfDSp6mU5D+4OG9DAkwHgwQMEqM
CZAKzAZgFUwDEA0MADAFwMAa//OCxEofsI4QAd8oANn////gRjv7lA6Mj9DnphUOsK9iUuij6ClD
NpVzNzzK+SsIu6K0hS2vb31++twklXN6bv5V5rdyCSEACMDSFVwAAOmABgBRgEIAoYD4Awn/2KOh
0AMgo/CwhRKU864DhSvRH6ImAenkTq/vsHGdXd2SzVe/dFR27dvrdeVfXN2t62Fjlo+EzK6b2PW6
hzjCDATQ52hPOOXdprl45ouRzN9tm5bUKkxBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqr/
84LEjxvJ/gwA/wpkqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqsscpl6iAADMDxFTDAAQBwwAQALM
AiAFzAfQG4/3lcHOfh4DH0SDyFqn34AQLNTTSi4AMvzor7cjviZLGq/p69XEdz3LQq9J5q3Vuekp
Kosw+QkU3bHoZuJMYJgM5qNL2EusswmfHxZt7Uab0vZz+UpMQU1FMy4xMDCqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqv/zgsSrG+FGDAD/CmSqqqqqqqqq
qqqqqqqqqqqq3rGagkhAAjBDBUEwAQAdMAFACjAIwBgwHwB9P7yZejnglAR6Dg6hcx2BwHGKzt+p
MB3RPZFfayWecK1f99qJs0Z99u5q0vtXKn0S7MmzC7tV7WoTe8/dbWomydUViOpPOltm7PZnpfb5
Vo7Mi8dGOiqpsrcYZfxzH0xBTUUzLjEwMFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVV//OCxLQeO24MAP8KZFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
VVVVVVXW61DBQ4ABmCUimhgA4A4YAMAFmARADpgPYEUfy23qnORUY8AIcHkaWpPxKLtbmv74AfWe
1v+4jsjbV2W1X1Kbr//buj+1X2p9o6kWXE4bLNb2sdY7ESxzF1O0Y2pH1yNsmG6CLXdu5p8iTEFN
RTMuMTAwqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqr/
84LEpRp5/gwA/wpoqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqrHKrNQSOgARgoQpKYAUANmADgB
hgEYA8YD0BLn7XPCxzQYmPQEGB1GpoMDhMSLZP64T19tsnuuJKhmv+6WXRY8zLps+9mvbZSWr9d1
9jiYpFR7xDUKJi2t1lcETayL7EoajC9UZZrmG3i+/Or6dFlMQU1FMy4xMDBVVVVVVVVVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVf/zgsSqG7n+DAD/CmRVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVVyxuVYCHAAEwV0UUMANAGjACAA0wCIAhMB5Aoj884EE5iNDHQFCA8
iK0KKBARM6a6UTATb3q1G7JsHW7K/ZLbbIo6xg5yy6ptB/fXhUpoqqSQelM9seW1mbWIQc6DjyZx
yMq8mcdFd0A55NRlj99YHUxBTUUzLjEwMFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVV//OCxKsb8UYMAP8KZFVVVVVVVVVVVVVVVVVVVVVVVVVVVd6q3IBG
QAIwXQUDMAOAGzACwAwwCMAiMB2Arz8IolY5YOzHIGCA6iM0GFzdarlYyJzLhPP7L7vp2DyIhVT1
k/V3Hpau9TypTOEp7CitgFNRdzQNVbCYqpTCKbDobIuFzlp/oYfHJy0jXTn0ls9PrHIY67a5TEFN
RTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/
84LErxzxRgwA/wpoVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVcsdUsFDAACYMaJ4GAIgDRgBQAaY
BIASmA7gXB9ociycpHxjgEg4NIis2gQQDr9W6u1Qhtqhivp96KK510aTmvVNm0/+htm1T10arKvp
mz0TeQaTQ5t9i3LS5bahZKq32J718U1zHLhKYDDHv8Uck+lMQU1FMy4xMDBVVVVVVVVVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVf/zgsSrHAIuDAD/CmRVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVVxyxmoiMgABg0Qm2YAoAMmAGgBhgEoBMYDkBin0nTIxyIimNwUDgy
jkzWRhYkI2u30wjm8v160uLLU6173a/ZDC6V0+r50d+iteX6/WlhVFp5xLRV5RDYa9JQ1aIQ/HXO
qRS1Hpax81Pu3IxRaqZtakxBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqq//OCxKsb2gIMAP8KZKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqst5
TMSQZMG5ExDAFwBgwAwANMAkAKTAcQM4+UmghOPkgxsDQUGkcWbSAYImbV9KrUJKnzUbe1rXFW3l
f/XSpBCw096E751imVMoQlKEpSVitqmi/ejgZjDzFsZrPvQbcbqLHWtxbPsM5pDp5mxilqN1TEFN
RTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/
84LErBwZRgwA/wpkVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX8saaAUERg5glaYAwAMmAHgBhgEoBU
YDcBsnwYU9RxgmmNQcCgqjk02TiIk2qfphenqiczaVwZKv+1nt3adXXXtR16MyzX7+mzN1dhQfFY
4Ez4BUSsIjxbbF7UVB5yDMmjdfWVYl41SGGWCnR3Icy4ohBMQU1FMy4xMDCqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqv/zgsStHHn+DAD/CmSqqqqqqqqq
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
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqv/zgsS5H1ouCAD+zmSqqqqqxys0
z+oZGFmB9JgGQAmYA2AJGATgIhgLwKmd5l/cH0QJlJEYMDoSmcyqzPWcnNZUpVsMsy+a5rbXV2o4
pS5rnvqd9NlPHHdUbRdXMld2sRa2d6pZFeduttT22T0dbZirq1d21VTrtNtQ52OSzTbehiO+/ecd
RkZ+hZs6BVKh1O8hXdc0bUxBTUUzLjEwMFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVV//OCxMAhK24IAP7OaFVVVVVVVVVVVVVVVVVVVVVV7jlSv8l6YT6G
hGAUgBRgCgAWYA8AcmAmglRzyPHud+4GPDpgIEkK1qZMBRYcqU9nwZ0T0s1NpXa4ktG/ZLVXZIv7
u6OtKyd7jx8R6WirjrzzkMRHJikuuLEZrFiA96xOa7w44aNkGToBWNOk1D6Vhg7VdQNq6WBpTEFN
RTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/
84LEsx3xogwA/spkVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVXHLHKMqBGFEBjJgFQAWYAq
AFGAOgHRgJAJics9z1HaOZjY4AANL5rM0WJFuZ6dA7X1+d+rjVr7rsuqvmZqK2qd9Nbt2b58/X+r
xq5gquCBotZTYl1DlrLFBqdD6e90y771bmplwy199kVlTSFMQU1FMy4xMDBVVVVVVVVVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVf/zgsSnGvH+DAD+zmRVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVVVdY5UsuUBMKTC7DAKwAgwBYALMAcAOzARQTQ45vrPOpdDGB0AgSX
rhTJcWkmbb0Sgb2+vRvbYlU17t2ui+YqFTXfT911u2ec3R5rdb+8kYovJrCrmXLyZLdYKEwMymHa
qZRGl3pLNSxZKhIxSFeiLkxBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqq//OCxKobugIMAP7OZKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq5lja
iqpjCnAr8wCwAHMAVACjAGwDowD4E5OGA7njnncxceAgGnM4NAOBhz119aAlfrTv3tYOpmq/far0
owltRquvb35GTT9Ms9L2Zurb2nerWzKraJ29EebRaFYv9p76TtS3NKtGZ26j97SGeW6Zu+g1TEFN
RTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/
84LErRx7bgwA/spkVVVVVVVVVVVVVVVVVVVVVVVVVe495FlSmFShRxgFoAIYAoAEmANAHZgHYJ4b
6n4vnJvBiQ+CQRKlpVCPBR9UX2UmB/+ne6lrYWyv+6Ep6vG21v6Oan2V3Z6/OumWzC7uUxaFTRSV
LnDIijNIqpsoSHXPvARR7G2hRZk8mYlFkHuVDiUrWumlQdVMQU1FMy4xMDBVVVVVVVVVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVf/zgsSxHWICDAD+ymRVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVXHvLUZWMYVYEvmAWAApgCoAQYAyAeGAbAoJuh3oUcM
8mHjwMBUqnRoCAuI3od0vhJp2s/+1FImzEbaf3Ttod879Krdm0b0emrpbq0zWve5RBVjJulbrHVy
YRaqvbdXvdo4/k23o7vz6kxBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqq//OCxKMZ2i4MAP7OZKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qtY9sxZYphWoRUYBeABGAKABJgCwB6YBiCiG1Z+05+fRjEINCJot2koaCj27/XA+/ul8/Tdwfsuu
S7J6pFVdN/3sS70qb0/27qyjRScvBckPF2TkUKusvGJQokG92jHux9u8eqPNC5jNNepVm69NTEFN
RTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/
84LEqRtp/gwA/opkVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVedvWp1dRhXQPqYBcAAmALgAxgC4
B4YBUCjmwdfGB7PpiUAUCp7N1iAIGjmWjeiYALbu29XtNfHE2q/b07qgtlnrZLVn75mTl9N0tS1L
f2fftXVfo+ZOtqdd9679E6uzbv0mak7fHaF22uxMXpp2h5VMQU1FMy4xMDBVVVVVVVVVVVVVVVVV
VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVf/zgsSrG9NyDAD+imRVVVVVVVVV
VVVVVVVVVVVVVVVVVcuZWZ5gphYIN4AgF4wBYAHMAUAPTAJQUg1af6pO/8MIhC4RPVu0fBwUWtP7
OuAdX82+2qsZYvSVUpRUZ19yMOQBXZG4MOAofQS1pfACQ25dMYhynjEmIop5qwIjTKhG7e/ckmli
Z24klo6A4cZQ5qSAun6yqkxBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqq//OCxLAdGUoMAP6KZKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qqqqqqrHK9fkLBjCxAYEDALpgCoAIYAmAeGAQApZpeX4Yc76YNAIAqhzYY4CBo4fSvu1QA17K7a/
bYUWq6NbdF0bd9aJ/o/7t6au1/0xaaqiYwl7Oga5elYuKiFGrYnXmHRfwhVSjJNc59t7kn21TEFN
RTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/
84LEpRpZ/gwA/opkVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX+ZXpcyUwskFCBwDEYAoACmAJA
HpgDIKYaAr+wnB/ABCIwihrZImDhg96LTumE6/Mvp97B9d1r3pVu6lFF99tXSiO77GXv9N33NQVM
tKSChewWpFnNMVbRVY+JnKuuqQ1r7dKExZJKHqS6mO0J5tZMQU1FMy4xMDCqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqv/zgsSqG7oCDAD+imSqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqv7y/Or+MLKBAQgBdMAVABDAEQDowBIFPM0C/oDYfwSgFA6i
zYYYBA0c6yP6rUBF/Wva8ycOEu7l/vtWin8rqlZL16Z/Vf71Slb210ve7U32/R9vRa+1ef26r7O9
f7GjFJz0V3xebgVdFNjTL0xBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqq//OCxKcbA0oMAP6KZKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qsudsydoJhZoFsGAMRgCgAGYAcAdmAGgpxk1P+iZ/8FkIyGVRbBE4vRX727dqYD/0VeXq13E037b
JdKbPFEbk30daSNyKnT1X/dhBdjosGANTHLk9N4wOEawSe2lKM69d5ZveitgoYzt99iLihhFTEFN
RTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/
84LEqRtp/gwA/opoVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVXneX5Ax47OGMOG
EwVAIwA0A6MAEBTzF2v+wDFfwIoASDh1haxyCoWzzdvrrJTQ61s/+vSMJYiMhRItFYnuKeLmMPbE
nUi+kvYm4RhhDvSupNAuooaYuvZTvvd+J5RxErcTY67voah2DAAgBoIAKAuAQmBCggZgmoGmYXOB
2mE5hTZgb4KoYQmDSGObF7BlM33uY/aVimRoidZhGYK+YE2ByP/zgsShGYDuDADv6EBguAJEYEYA
OGAGAJhgNgCgAgBEtey+SLkYJHQ1A4GVD1G3F8QDWPQZEVjZ5D8UDWTg6JoceRWMkM5FBEXb/Dxk
yrGSl9+lLsDzX3iTVqRP8+nv8fefr/dsfG7/5v//feL79NX3v7n5jHhl3dLD/Iz57U6en+HmrP+O
rv//f+TtO/BBY/gmxn/EmPt8mO5LgP62Q7wAAgggQggBjXD7GRALEYAADRhfjIPtJTMGGwNJ6ewy
gzPDF1LOgh9jsFHTMPUIkyfQ//OCxP8zwgIMAV94AeoxBBq5+yaTZnz45xp2Y6iGShZqDr+WzQmM
7m/OlTzCSYSNjECv/81gJNbcTbzUFVAFFAMTCIFCoR//5kaCaSQmkBwBHzLREw0AcsRgACCldf//
5kwQjqBhMxoIV6guYcDJ7FmkHmZIBkA0Bf///+JBDOzDgwFBkmMABgEGKwF5EvkJVAuZE7jpJfUv
/////5bRajVEAiljlImKWNSUwUsX+0iSLmlNIyqIzr7RGKzURh3////////2mMnjjiMHpocZfRz/
84LE9FBbwjhTntgAsa/F8HLfu3eiL+y2Zf2HZl/X9uwy7O5S7P//////////vu78/E3Li8y7b9y1
237k0Nv3Akrh9+Lsv7VdnK7DNbOU1rUzNS7c1Lu1o1TKTEFNRTMuMTAwqqqqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpMQU1FMy4xMDCqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqv/zgsQ7AAADSAHAAACqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
qqqqqqqqqqqqqqqqqqqqqqqq
"""


class Synthesizer:
    """Abstract synthesizer interface."""

    name: str = "base"

    def available_voices(self) -> List[str]:  # pragma: no cover - convenience wrapper
        return ["neutral"]

    async def synthesize(self, text: str, voice: str, speed: float) -> bytes:
        raise NotImplementedError


class DummySynthesizer(Synthesizer):
    """Synthesizer that returns a canned tone to simulate audio output."""

    name = "dummy"

    def __init__(self) -> None:
        self._payload = base64.b64decode(_PLACEHOLDER_MP3_BASE64.encode("ascii"))
        self._voices = ["neutral", "calm", "bright"]

    def available_voices(self) -> List[str]:  # pragma: no cover - trivial
        return list(self._voices)

    async def synthesize(self, text: str, voice: str, speed: float) -> bytes:
        # Simulate processing latency relative to text length and speed.
        await asyncio.sleep(min(0.1 + len(text) / 200.0, 1.0))
        # Return placeholder audio bytes. Real implementation would call a TTS model here.
        return self._payload


@dataclass
class PipelineResult:
    audio_path: Path
    subtitle_path: Path


class SynthesisPipeline:
    """Coordinate synthesis jobs and update the shared job manager."""

    def __init__(self, manager: JobManager, synthesizer: Synthesizer | None = None) -> None:
        self.manager = manager
        self.synthesizer = synthesizer or DummySynthesizer()

    async def run(
        self,
        job_id: str,
        segments: Iterable[str],
        voice: str,
        speed: float,
    ) -> PipelineResult:
        state = await self.manager.get_job(job_id)
        segments_list = [segment.strip() for segment in segments if segment.strip()]
        if not segments_list:
            raise ValueError("No content found in the provided text file")

        await self.manager.update(job_id, status="running", progress=0.0, message="Starting synthesis")

        audio_path = state.output_dir / "output.mp3"
        subtitle_path = state.output_dir / "subtitles.srt"

        progress_step = 1.0 / len(segments_list)
        audio_chunks: List[bytes] = []
        subtitle_lines: List[str] = []

        for index, text in enumerate(segments_list, start=1):
            try:
                audio_bytes = await self.synthesizer.synthesize(text, voice, speed)
            except Exception as exc:  # pragma: no cover - simple error propagation
                await self.manager.update(
                    job_id,
                    status="failed",
                    message="Synthesis failed",
                    error=str(exc),
                )
                raise

            audio_chunks.append(audio_bytes)
            start_seconds = (index - 1) * 2
            end_seconds = index * 2
            subtitle_lines.append(self._format_srt_entry(index, start_seconds, end_seconds, text))

            await self.manager.update(
                job_id,
                progress=round(min(progress_step * index, 1.0), 4),
                message=f"Processed segment {index}/{len(segments_list)}",
            )

        audio_path.write_bytes(b"".join(audio_chunks))
        subtitle_path.write_text("\n".join(subtitle_lines), encoding="utf-8")

        await self.manager.update(
            job_id,
            status="completed",
            progress=1.0,
            message="Synthesis complete",
            audio_path=audio_path,
            subtitle_path=subtitle_path,
        )

        return PipelineResult(audio_path=audio_path, subtitle_path=subtitle_path)

    @staticmethod
    def _format_srt_entry(index: int, start_seconds: int, end_seconds: int, text: str) -> str:
        return "\n".join(
            [
                str(index),
                f"{SynthesisPipeline._format_timestamp(start_seconds)} --> {SynthesisPipeline._format_timestamp(end_seconds)}",
                text,
                "",
            ]
        )

    @staticmethod
    def _format_timestamp(total_seconds: int) -> str:
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},000"


__all__ = ["DummySynthesizer", "PipelineResult", "SynthesisPipeline", "Synthesizer"]
