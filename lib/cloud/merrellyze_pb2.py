# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: merrellyze.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='merrellyze.proto',
  package='merrellyze',
  syntax='proto3',
  serialized_pb=_b('\n\x10merrellyze.proto\x12\nmerrellyze\"!\n\x05Image\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x0c\n\x04path\x18\x03 \x01(\t\"@\n\x10\x43\x61ptureJobRecord\x12\n\n\x02id\x18\x01 \x01(\x05\x12 \n\x05image\x18\x02 \x03(\x0b\x32\x11.merrellyze.Image\"A\n\x14\x45llipseSearchRequest\x12)\n\x03\x63jr\x18\x01 \x03(\x0b\x32\x1c.merrellyze.CaptureJobRecord\"4\n\x15\x45rrorCJREllipseSearch\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x0f\n\x07message\x18\x02 \x01(\t\"\x8c\x01\n\x15\x45llipseSearchResponse\x12\x36\n\x10\x63jrs_in_progress\x18\x01 \x03(\x0b\x32\x1c.merrellyze.CaptureJobRecord\x12;\n\x10\x63jrs_with_errors\x18\x02 \x03(\x0b\x32!.merrellyze.ErrorCJREllipseSearch\":\n\rResultRequest\x12)\n\x03\x63jr\x18\x01 \x03(\x0b\x32\x1c.merrellyze.CaptureJobRecord\" \n\x08Location\x12\t\n\x01x\x18\x01 \x01(\x05\x12\t\n\x01y\x18\x02 \x01(\x05\"f\n\nEllipseTag\x12\x10\n\x08image_id\x18\x01 \x01(\x05\x12#\n\x05start\x18\x02 \x01(\x0b\x32\x14.merrellyze.Location\x12!\n\x03\x65nd\x18\x03 \x01(\x0b\x32\x14.merrellyze.Location\"@\n\rEllipseTagCJR\x12\n\n\x02id\x18\x01 \x03(\x05\x12#\n\x03tag\x18\x02 \x03(\x0b\x32\x16.merrellyze.EllipseTag\"p\n\x0eResultResponse\x12(\n\x05ready\x18\x01 \x03(\x0b\x32\x19.merrellyze.EllipseTagCJR\x12\x34\n\tnot_ready\x18\x02 \x01(\x0b\x32!.merrellyze.EllipseSearchResponse2i\n\x0f\x45llipseSearcher\x12V\n\rEllipseSearch\x12 .merrellyze.EllipseSearchRequest\x1a!.merrellyze.EllipseSearchResponse\"\x00\x62\x06proto3')
)
_sym_db.RegisterFileDescriptor(DESCRIPTOR)




_IMAGE = _descriptor.Descriptor(
  name='Image',
  full_name='merrellyze.Image',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='merrellyze.Image.id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='path', full_name='merrellyze.Image.path', index=1,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=32,
  serialized_end=65,
)


_CAPTUREJOBRECORD = _descriptor.Descriptor(
  name='CaptureJobRecord',
  full_name='merrellyze.CaptureJobRecord',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='merrellyze.CaptureJobRecord.id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='image', full_name='merrellyze.CaptureJobRecord.image', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=67,
  serialized_end=131,
)


_ELLIPSESEARCHREQUEST = _descriptor.Descriptor(
  name='EllipseSearchRequest',
  full_name='merrellyze.EllipseSearchRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cjr', full_name='merrellyze.EllipseSearchRequest.cjr', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=133,
  serialized_end=198,
)


_ERRORCJRELLIPSESEARCH = _descriptor.Descriptor(
  name='ErrorCJREllipseSearch',
  full_name='merrellyze.ErrorCJREllipseSearch',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='merrellyze.ErrorCJREllipseSearch.id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='message', full_name='merrellyze.ErrorCJREllipseSearch.message', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=200,
  serialized_end=252,
)


_ELLIPSESEARCHRESPONSE = _descriptor.Descriptor(
  name='EllipseSearchResponse',
  full_name='merrellyze.EllipseSearchResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cjrs_in_progress', full_name='merrellyze.EllipseSearchResponse.cjrs_in_progress', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cjrs_with_errors', full_name='merrellyze.EllipseSearchResponse.cjrs_with_errors', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=255,
  serialized_end=395,
)


_RESULTREQUEST = _descriptor.Descriptor(
  name='ResultRequest',
  full_name='merrellyze.ResultRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cjr', full_name='merrellyze.ResultRequest.cjr', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=397,
  serialized_end=455,
)


_LOCATION = _descriptor.Descriptor(
  name='Location',
  full_name='merrellyze.Location',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='x', full_name='merrellyze.Location.x', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y', full_name='merrellyze.Location.y', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=457,
  serialized_end=489,
)


_ELLIPSETAG = _descriptor.Descriptor(
  name='EllipseTag',
  full_name='merrellyze.EllipseTag',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='image_id', full_name='merrellyze.EllipseTag.image_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='start', full_name='merrellyze.EllipseTag.start', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='end', full_name='merrellyze.EllipseTag.end', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=491,
  serialized_end=593,
)


_ELLIPSETAGCJR = _descriptor.Descriptor(
  name='EllipseTagCJR',
  full_name='merrellyze.EllipseTagCJR',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='merrellyze.EllipseTagCJR.id', index=0,
      number=1, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='tag', full_name='merrellyze.EllipseTagCJR.tag', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=595,
  serialized_end=659,
)


_RESULTRESPONSE = _descriptor.Descriptor(
  name='ResultResponse',
  full_name='merrellyze.ResultResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='ready', full_name='merrellyze.ResultResponse.ready', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='not_ready', full_name='merrellyze.ResultResponse.not_ready', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=661,
  serialized_end=773,
)

_CAPTUREJOBRECORD.fields_by_name['image'].message_type = _IMAGE
_ELLIPSESEARCHREQUEST.fields_by_name['cjr'].message_type = _CAPTUREJOBRECORD
_ELLIPSESEARCHRESPONSE.fields_by_name['cjrs_in_progress'].message_type = _CAPTUREJOBRECORD
_ELLIPSESEARCHRESPONSE.fields_by_name['cjrs_with_errors'].message_type = _ERRORCJRELLIPSESEARCH
_RESULTREQUEST.fields_by_name['cjr'].message_type = _CAPTUREJOBRECORD
_ELLIPSETAG.fields_by_name['start'].message_type = _LOCATION
_ELLIPSETAG.fields_by_name['end'].message_type = _LOCATION
_ELLIPSETAGCJR.fields_by_name['tag'].message_type = _ELLIPSETAG
_RESULTRESPONSE.fields_by_name['ready'].message_type = _ELLIPSETAGCJR
_RESULTRESPONSE.fields_by_name['not_ready'].message_type = _ELLIPSESEARCHRESPONSE
DESCRIPTOR.message_types_by_name['Image'] = _IMAGE
DESCRIPTOR.message_types_by_name['CaptureJobRecord'] = _CAPTUREJOBRECORD
DESCRIPTOR.message_types_by_name['EllipseSearchRequest'] = _ELLIPSESEARCHREQUEST
DESCRIPTOR.message_types_by_name['ErrorCJREllipseSearch'] = _ERRORCJRELLIPSESEARCH
DESCRIPTOR.message_types_by_name['EllipseSearchResponse'] = _ELLIPSESEARCHRESPONSE
DESCRIPTOR.message_types_by_name['ResultRequest'] = _RESULTREQUEST
DESCRIPTOR.message_types_by_name['Location'] = _LOCATION
DESCRIPTOR.message_types_by_name['EllipseTag'] = _ELLIPSETAG
DESCRIPTOR.message_types_by_name['EllipseTagCJR'] = _ELLIPSETAGCJR
DESCRIPTOR.message_types_by_name['ResultResponse'] = _RESULTRESPONSE

Image = _reflection.GeneratedProtocolMessageType('Image', (_message.Message,), dict(
  DESCRIPTOR = _IMAGE,
  __module__ = 'merrellyze_pb2'
  # @@protoc_insertion_point(class_scope:merrellyze.Image)
  ))
_sym_db.RegisterMessage(Image)

CaptureJobRecord = _reflection.GeneratedProtocolMessageType('CaptureJobRecord', (_message.Message,), dict(
  DESCRIPTOR = _CAPTUREJOBRECORD,
  __module__ = 'merrellyze_pb2'
  # @@protoc_insertion_point(class_scope:merrellyze.CaptureJobRecord)
  ))
_sym_db.RegisterMessage(CaptureJobRecord)

EllipseSearchRequest = _reflection.GeneratedProtocolMessageType('EllipseSearchRequest', (_message.Message,), dict(
  DESCRIPTOR = _ELLIPSESEARCHREQUEST,
  __module__ = 'merrellyze_pb2'
  # @@protoc_insertion_point(class_scope:merrellyze.EllipseSearchRequest)
  ))
_sym_db.RegisterMessage(EllipseSearchRequest)

ErrorCJREllipseSearch = _reflection.GeneratedProtocolMessageType('ErrorCJREllipseSearch', (_message.Message,), dict(
  DESCRIPTOR = _ERRORCJRELLIPSESEARCH,
  __module__ = 'merrellyze_pb2'
  # @@protoc_insertion_point(class_scope:merrellyze.ErrorCJREllipseSearch)
  ))
_sym_db.RegisterMessage(ErrorCJREllipseSearch)

EllipseSearchResponse = _reflection.GeneratedProtocolMessageType('EllipseSearchResponse', (_message.Message,), dict(
  DESCRIPTOR = _ELLIPSESEARCHRESPONSE,
  __module__ = 'merrellyze_pb2'
  # @@protoc_insertion_point(class_scope:merrellyze.EllipseSearchResponse)
  ))
_sym_db.RegisterMessage(EllipseSearchResponse)

ResultRequest = _reflection.GeneratedProtocolMessageType('ResultRequest', (_message.Message,), dict(
  DESCRIPTOR = _RESULTREQUEST,
  __module__ = 'merrellyze_pb2'
  # @@protoc_insertion_point(class_scope:merrellyze.ResultRequest)
  ))
_sym_db.RegisterMessage(ResultRequest)

Location = _reflection.GeneratedProtocolMessageType('Location', (_message.Message,), dict(
  DESCRIPTOR = _LOCATION,
  __module__ = 'merrellyze_pb2'
  # @@protoc_insertion_point(class_scope:merrellyze.Location)
  ))
_sym_db.RegisterMessage(Location)

EllipseTag = _reflection.GeneratedProtocolMessageType('EllipseTag', (_message.Message,), dict(
  DESCRIPTOR = _ELLIPSETAG,
  __module__ = 'merrellyze_pb2'
  # @@protoc_insertion_point(class_scope:merrellyze.EllipseTag)
  ))
_sym_db.RegisterMessage(EllipseTag)

EllipseTagCJR = _reflection.GeneratedProtocolMessageType('EllipseTagCJR', (_message.Message,), dict(
  DESCRIPTOR = _ELLIPSETAGCJR,
  __module__ = 'merrellyze_pb2'
  # @@protoc_insertion_point(class_scope:merrellyze.EllipseTagCJR)
  ))
_sym_db.RegisterMessage(EllipseTagCJR)

ResultResponse = _reflection.GeneratedProtocolMessageType('ResultResponse', (_message.Message,), dict(
  DESCRIPTOR = _RESULTRESPONSE,
  __module__ = 'merrellyze_pb2'
  # @@protoc_insertion_point(class_scope:merrellyze.ResultResponse)
  ))
_sym_db.RegisterMessage(ResultResponse)


from grpc.beta import implementations as beta_implementations
from grpc.beta import interfaces as beta_interfaces
from grpc.framework.common import cardinality
from grpc.framework.interfaces.face import utilities as face_utilities


class BetaEllipseSearcherServicer(object):
  def EllipseSearch(self, request, context):
    context.code(beta_interfaces.StatusCode.UNIMPLEMENTED)


class BetaEllipseSearcherStub(object):
  def EllipseSearch(self, request, timeout, metadata=None, with_call=False, protocol_options=None):
    raise NotImplementedError()
  EllipseSearch.future = None


def beta_create_EllipseSearcher_server(servicer, pool=None, pool_size=None, default_timeout=None, maximum_timeout=None):
  request_deserializers = {
    ('merrellyze.EllipseSearcher', 'EllipseSearch'): EllipseSearchRequest.FromString,
  }
  response_serializers = {
    ('merrellyze.EllipseSearcher', 'EllipseSearch'): EllipseSearchResponse.SerializeToString,
  }
  method_implementations = {
    ('merrellyze.EllipseSearcher', 'EllipseSearch'): face_utilities.unary_unary_inline(servicer.EllipseSearch),
  }
  server_options = beta_implementations.server_options(request_deserializers=request_deserializers, response_serializers=response_serializers, thread_pool=pool, thread_pool_size=pool_size, default_timeout=default_timeout, maximum_timeout=maximum_timeout)
  return beta_implementations.server(method_implementations, options=server_options)


def beta_create_EllipseSearcher_stub(channel, host=None, metadata_transformer=None, pool=None, pool_size=None):
  request_serializers = {
    ('merrellyze.EllipseSearcher', 'EllipseSearch'): EllipseSearchRequest.SerializeToString,
  }
  response_deserializers = {
    ('merrellyze.EllipseSearcher', 'EllipseSearch'): EllipseSearchResponse.FromString,
  }
  cardinalities = {
    'EllipseSearch': cardinality.Cardinality.UNARY_UNARY,
  }
  stub_options = beta_implementations.stub_options(host=host, metadata_transformer=metadata_transformer, request_serializers=request_serializers, response_deserializers=response_deserializers, thread_pool=pool, thread_pool_size=pool_size)
  return beta_implementations.dynamic_stub(channel, 'merrellyze.EllipseSearcher', cardinalities, options=stub_options)
# @@protoc_insertion_point(module_scope)
