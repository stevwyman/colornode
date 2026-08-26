# Third-party notices

This service vendors inference code from [DDColor](https://github.com/piddnad/DDColor)
(Apache License 2.0), including the `ddcolor` package and
`basicsr/archs/ddcolor_arch_utils` helpers required at runtime.

Pretrained weights are downloaded from Hugging Face (`piddnad/ddcolor_*`) on
first use and stored under `DDCOLOR_HOME`. They are not redistributed in this
repository.

ConvNeXt encoder code includes a Meta Platforms copyright notice; see
`basicsr/archs/ddcolor_arch_utils/convnext.py`.
