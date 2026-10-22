# Ground truth spot-check

For each PR: do the issues match what the humans actually said?

## fastapi/fastapi#16043  🐛 Fix `exclude_defaults` not propagated to dict keys and values in `jsonable_encoder`

Human comments:
- `tests/test_jsonable_encoder.py` (YuriiMotov): ```suggestion     assert jsonable_encoder({"key": model}) == {"key": {"foo": "foo", "bar": "bar"}} ```  We are testing `exclude_defaults` here. No need to add `exclude_unset` and `exclude_none` - it will only mislead future readers
- `fastapi/encoders.py` (YuriiMotov): Just a note, no need to change this for now. Passing it to the recursive call for dict keys is not strictly needed - currently tests doesn't cover this and I couldn't come up with use case for this. But we can still keep it just for the symmetry

Extracted issues:
1. `tests/test_jsonable_encoder.py`: The test should not include exclude_unset and exclude_none parameters when testing exclude_defaults, as it may mislead future readers.

## fastapi/fastapi#15515  🐛 Fix line splitting in `format_sse_event` to comply with SSE spec

Human comments:
- `fastapi/sse.py` (YuriiMotov): ```suggestion ```  I think we should shorten code comment. You can add this long explanation as a review comment
- `tests/test_sse.py` (YuriiMotov): ```suggestion @pytest.mark.parametrize(     ("data", "expected_result"),     [         ("Hello\n", b"data: Hello\ndata: \n\n"),         ("Hello\n\n", b"data: Hello\ndata: \ndata: \n\n"),         ("\n", b"data: \ndata: \n\n"),         ("Hello\r\nWorld", b"data: Hello\ndata: World\n\n"),         ("Hello\rWorld", b"data: Hello\ndata: World\n\n"),         ("A\u2028B", "data: A\u2028B\n\n".encode()),  
- `tests/test_sse.py` (YuriiMotov): Let's also add the test case with empty data string from PR https://github.com/fastapi/fastapi/pull/15618:  ```py def test_format_sse_event_keeps_empty_data_line():     payload = format_sse_event(data_str="")     assert payload == b"data: \n\n" ```

Extracted issues:
1. `fastapi/sse.py`: The code comment explaining line splitting in _split_sse_lines is too long and should be shortened, with the detailed explanation moved to a review comment.
2. `tests/test_sse.py`: The tests for format_sse_event should be shortened and parameterized, and the Unicode character U+2028 should be represented by its code to avoid VSCode warnings.
3. `tests/test_sse.py`: A test case should be added to verify that format_sse_event correctly handles an empty data string by emitting a data line with an empty value.

## fastapi/fastapi#15101  ⬆️ Update Pydantic v2 code to address deprecations

Human comments:
- `fastapi/_compat/v2.py` (YuriiMotov): As an alternative, we can use `try...except`:  ```py     try:             return _pydantic_typing_extra.try_eval_type(value, globalns, localns)[0]     except AttrbuteError:         return _pydantic_typing_extra.eval_type_lenient(  # ty: ignore[deprecated]             value, globalns, localns         )  # pragma: no cover ``` Or move this to module level, and only use it inside `evaluate_forwardref
- `fastapi/_compat/v2.py` (Viicos): I found it a bit unfortunate that this PR still relies on an internal function.. The only reason I kept `eval_type_lenient()` in Pydantic was because FastAPI was using it, and now the same issue exists with `try_eval_type()`.
- `fastapi/_compat/v2.py` (Viicos): I think it might be worth solving this cleanly, that is by first having the ability to do such evaluations using the stdlib. I proposed https://discuss.python.org/t/100698 a while ago, I'll try to continue working on it. Then we could see how can this be used in FastAPI/Pydantic!

Extracted issues:
1. `fastapi/_compat/v2.py`: The code still relies on internal Pydantic functions (such as try_eval_type), which is undesirable and may cause maintenance issues.

## fastapi/fastapi#15077  🐛 Fix stream item type lost when using `include_router()`

Human comments:
- `tests/test_sse.py` (YuriiMotov): I would rename `c` to `client` here and in other test functions. Also, you can actually get OpenAPI schema directly as `default_app_app.openapi()`
- `tests/test_sse.py` (YuriiMotov): Maybe better make it return the same as `stream_events_typed` above for consistency. And the same for `default_parent_stream`.  But not critical for me

Extracted issues:
1. `tests/test_sse.py`: The variable 'c' should be renamed to 'client' in test functions for clarity.
2. `tests/test_sse.py`: The test endpoint 'default_app_stream' and 'default_parent_stream' should return the same data as 'stream_events_typed' for consistency.

## fastapi/fastapi#14874  🐛 Fix handling sequences with nested Annotated types

Human comments:
- `tests/test_nested_annotated_in_sequence.py` (clefeu): Why don't you use `MaxSizedSet | None`?

Extracted issues:
1. `tests/test_nested_annotated_in_sequence.py`: The code uses 'Annotated[Union[MaxSizedSet, None], Query()]' instead of the more idiomatic 'MaxSizedSet | None'.

## fastapi/fastapi#14828  ✅ Test order for the submitted byte Files

Human comments:
- `tests/test_list_bytes_file_order_preserved_issue_14811.py` (YuriiMotov): ```suggestion def test_list_bytes_file_preserves_order( ```

Extracted issues:
1. `tests/test_list_bytes_file_order_preserved_issue_14811.py`: The test function name should be changed to test_list_bytes_file_preserves_order for clarity and consistency.

## fastapi/fastapi#14809  📝 Add banner to translated pages

Human comments:
- `scripts/mkdocs_hooks.py` (tiangolo): Looking at this I'm realizing that we already have the data to put there a link to the original in English, that might help.  We could add an:  ```Markdown [English version](https://blahblah/link) ```

Extracted issues:
1. `scripts/mkdocs_hooks.py`: The translation banner should include a link to the original English version of the page.

## fastapi/fastapi#14616  🐛 Fix using `Json[list[str]]` type (issue #10997)

Human comments:
- `fastapi/dependencies/utils.py` (YuriiMotov): ```suggestion     return any(isinstance(item, Json) for item in field.field_info.metadata) ```  FastAPI dropped the support of Pydantic V1 recently. We can now simplify this. Also, we should use `isinstance` to check type
- `fastapi/dependencies/utils.py` (YuriiMotov): ```suggestion     if (         (not _is_json_field(field))         and is_sequence_field(field)         and isinstance(values, (ImmutableMultiDict, Headers))     ): ```
- `tests/test_form_json_type.py` (YuriiMotov): ```suggestion ``` I think we don't need this test
- `tests/test_form_json_type.py` (YuriiMotov): ```suggestion ``` I think we don't need this

Extracted issues:
1. `fastapi/dependencies/utils.py`: The type check for Json fields should use isinstance and can be simplified since FastAPI no longer supports Pydantic V1.
2. `fastapi/dependencies/utils.py`: The logic for handling _is_json_field in _get_multidict_value should be inverted to avoid unnecessary branching.

## fastapi/fastapi#14434  ♻️ Refactor internals, update `is_coroutine` check to reuse internal supported variants (unwrap, check class)

Human comments:
- `fastapi/routing.py` (dolfinus): Why keeping this condition with empty branches?

Extracted issues:
1. `fastapi/routing.py`: There is an if condition for Python 3.13 or higher with an empty branch, which should be removed or handled properly.

## psf/requests#7502  Fix `_encode_files` detection for `__getattr__`-based file wrappers

Human comments:
- `tests/test_requests.py` (nateprewitt): I'm not sure we need both of these tests. Either class encompasses the behavior we're trying to guard against, and if we truly need both, the test should be parameterized.  I'd bias towards removing the second though.
- `tests/test_requests.py` (nateprewitt): Do we actually need `data` or `params`? The behavior should trigger with just `files`. Let's only use that to keep the tests intent clear.
- `tests/test_requests.py` (nateprewitt): Sure, `NamedTemporaryFile` is fine for the test if that catches the wrapper issue.

Extracted issues:
1. `tests/test_requests.py`: The test should only use 'files' and omit unnecessary 'data' or 'params' arguments to keep the test's intent clear.
2. `tests/test_requests.py`: There is redundancy between the two tests for file wrapper behavior and either one should be removed or the tests should be parameterized.

## psf/requests#7496  Improve static typing of 3rd party imports 

Human comments:
- `src/requests/compat.py` (nateprewitt): I think this change isn't quite right. We're now type checking against the wrong character detection library and losing type nuance for what actually gets returned by `_resolve_char_detection` at runtime.  That's not the end of the world, because I don't think we're truly making use of the 3p types, but is probably something we want to align with the actual default behavior of Requests in the futu

Extracted issues:
1. `src/requests/compat.py`: The change causes type checking to use the wrong character detection library and loses type nuance for what is actually returned by _resolve_char_detection at runtime.

## psf/requests#7436  Update JsonType containers to read-based collections

Human comments:
- `src/requests/_types.py` (JamMarHer): Consider making the following update as well:  ```suggestion         None | bool | int | float | str | Sequence["JsonType"] | Mapping[str, "JsonType"] ```
- `src/requests/_types.py` (JamMarHer): Just saw your other comment https://github.com/psf/requests/issues/7434#issuecomment-4433151990. 🙇🏼

Extracted issues:
1. `src/requests/_types.py`: The JsonType type alias should use Sequence instead of list to allow for more general read-based collections.

## psf/requests#7433  Fix `prepare_body` stream detection for `__getattr__`-based file wrappers

Human comments:
- `src/requests/models.py` (nateprewitt): ```suggestion         # data that proxies attributes to underlying objects needs hasattr         is_iterable = isinstance(data, Iterable) or hasattr(data, "__iter__")         if is_iterable and not isinstance( ```

Extracted issues:
1. `src/requests/models.py`: The code should assign the result of the iterable check to a variable for clarity before using it in the conditional.

## psf/requests#7431  Fix mutability issues with headers input types

Human comments:
- `src/requests/models.py` (sigmavirus24): Why not headerstype here too?
- `src/requests/_types.py` (sdm0p): ⚠️ **HIGH** — *test_coverage*   **Confidence:** 70%    New logic without tests: The `HeadersType` has been changed to `MutableMapping[str, str | bytes] | None` without adding corresponding tests.  **Suggested fix:** ``` Add tests to cover the new `HeadersType` logic. ```
- `src/requests/models.py` (sdm0p): 📌 **MEDIUM** — *test_coverage*   **Confidence:** 70%    Modified behaviour without updated assertions: The `Request` class's `__init__` method now uses the new `HeadersType` without updating the corresponding tests.  **Suggested fix:** ``` Update the tests for the `Request` class's `__init__` method to cover the new `HeadersType` logic. ```
- `src/requests/_types.py` (sdm0p): ⚠️ **HIGH** — *test_coverage*   **Confidence:** 80%    New logic for handling MutableMapping in Request.headers is not tested.  **Suggested fix:** ``` Add test cases to cover the new logic for handling MutableMapping in Request.headers. ```

Extracted issues:
1. `src/requests/_types.py`: The new logic for handling MutableMapping in HeadersType and Request.headers is not covered by tests.
2. `src/requests/models.py`: The tests for the Request class's __init__ method have not been updated to cover the new HeadersType logic.

## psf/requests#6865  Update docstring for Session.verify to include string support (#6859)

Human comments:
- `src/requests/sessions.py` (nateprewitt): Let's keep the `False` warning attached to the rest of the `False` information, it may be easy to miss if you stop reading at that point.  ```suggestion         #: Only set this to `False` for testing.         #: If verify is set to a string, it must be the path to a CA bundle file         #: that will be used to verify the TLS certificate. ```

Extracted issues:
1. `src/requests/sessions.py`: The warning about setting verify to False should remain attached to the rest of the False-related information to avoid it being overlooked.

## psf/requests#6757  Test on urllib3 1.26.x

Human comments:
- `src/requests/compat.py` (sethmlarson): I believe this is a string, not an integer. Also, should do a >= check instead of equals.

Extracted issues:
1. `src/requests/compat.py`: The code checks if the major version of urllib3 is 2 using string equality instead of converting to integer and using a greater-than-or-equal check, which could cause incorrect detection for future versions.

## psf/requests#6724  Don't create default SSLContext if ssl module isn't present

Human comments:
- `src/requests/adapters.py` (sigmavirus24): Missed this earlier but do we need any logic for verify=True without a condition here?
- `src/requests/adapters.py` (sigmavirus24): Makes sense. I've a terrible headache so just looking at the branches and concerned about missing something is all.
- `src/requests/adapters.py` (sigmavirus24): Oh, looking again, not on a phone, and without a migraine, I see the `cert_reqs = "CERT_REQUIRED"` line on L110 that I clearly wrote, and which is what I was thinking we may want to be concerned about. So, I'm not nearly as worried.
- `src/requests/adapters.py` (sigmavirus24): Looking at this again with something of a performance mindset, do we want to cache somehow lookups to `isdir`? I'm not sure this hurts us at all, but just thinking about things that could slow us down in certain cases now. (Not for this pull request, just putting it out there)

Extracted issues:
1. `src/requests/adapters.py`: The logic for handling verify=True may be missing a necessary condition or case.

## psf/requests#6710  Move _get_connection to get_connection_with_tls_context

Human comments:
- `src/requests/adapters.py` (sethmlarson): If this method is deprecated shall we start emitting `DeprecationWarning`?

Extracted issues:
1. `src/requests/adapters.py`: The deprecated method should emit a DeprecationWarning when used.

## psf/requests#6702  Allow optional char detection dependencies in post-packaging

Human comments:
- `src/requests/compat.py` (nijel): While this keeps the logic of the earlier code, I think that the library which is required on should be tried first. https://github.com/psf/requests/pull/6714 addresses this.

Extracted issues:
1. `src/requests/compat.py`: The code should try to import the character detection library that is required or preferred first, rather than trying them in a fixed order.

## encode/httpx#3371  Review URL percent escaping sets, from whatwg.

Human comments:
- `tests/models/test_url.py` (elupus): This looks weird. I could be wrong. But should the userinfo field contain partial escapes? The trialing % sign change here seem odd.

Extracted issues:
1. `tests/models/test_url.py`: The userinfo field may incorrectly contain a trailing percent sign, suggesting partial or incorrect percent-escaping.

## encode/httpx#3312  Clarified error when header value is None

Human comments:
- `tests/test_utils.py` (lovelydinosaur): Could we have these tests in `tests/client/test_headers.py` with the testing against `httpx.Header(...)` instead of against the internal API?

Extracted issues:
1. `tests/test_utils.py`: The tests for header value normalization should be located in tests/client/test_headers.py and should test against the public httpx.Header API instead of the internal normalize_header_value function.

## encode/httpx#3250  Improve InvalidURL error message.

Human comments:
- `httpx/_urlparse.py` (adriangb): Could this be done lazily without materializing the list?
- `httpx/_urlparse.py` (adriangb): Same here. This could be a small utility function as well (it's duplicated in 2 places, I'm okay keeping it duplicated).

Extracted issues:
1. `httpx/_urlparse.py`: The code unnecessarily materializes a list to find the first non-printable ASCII character, which could be done lazily to improve performance.

## encode/httpx#3245  Clean up URL signature.

Human comments:
- `httpx/_api.py` (T-256): could it be under `typing.TYPE_CHECKING`?

Extracted issues:
1. `httpx/_api.py`: The import of URL from ._urls could be moved under typing.TYPE_CHECKING to avoid unnecessary runtime import.

## encode/httpx#3045  Fix RFC 2069 mode digest authentication

Human comments:
- `httpx/_auth.py` (lovelydinosaur): Looking at the curl code, seems like this change should be the other way around(?)...  ```python         if qop is None:             digest_data = [HA1, challenge.nonce, HA2]         else:             digest_data = [HA1, challenge.nonce, nc_value, cnonce, qop, HA2] ```  And then...  ```python         format_args = {             "username": self._username,             "realm": challen

Extracted issues:
1. `httpx/_auth.py`: The code incorrectly omits HA1 from the digest_data list when qop is None, which does not match the expected behavior for RFC 2069 digest authentication.

## encode/httpx#2990  Cleanup URL percent-encoding behavior.

Human comments:
- `httpx/_urlparse.py` (karpetrosyan): I believe we should also add unit tests for these functions, rather than simply testing them with `httpx.URL`.  This would be a more robust approach, in my opinion.
- `httpx/_urlparse.py` (T-256): IMO current approach is fine.  > This is clearly a code-smell, because our test cases ought to be tests against our public API, rather than testing implementation details. Perhaps there's some cases where it's a necessary hack, but... perhaps not?   from https://github.com/encode/httpx/issues/2492#issue-1478857204
- `httpx/_urlparse.py` (zanieb): I agree testing the public API should be sufficient unless something private is particularly expensive to test via the public API.
- `httpx/_urlparse.py` (karpetrosyan): It's a matter of preference, but if we encounter regression in our `httpx.URL` tests, we will go through these functions and find the method that isn't working properly, which is why unit tests are useful.

Extracted issues:
1. `httpx/_urlparse.py`: Unit tests should be added for the quote function rather than relying solely on tests of httpx.URL.

## encode/httpx#2911  Cleanup `response.json()` method.

Human comments:
- `httpx/_models.py` (alexmojaki): Just a random thing I noticed looking through the code, not a problem I've seen in the wild: isn't using `self.text` like this this better than the new version when there's a non-utf charset?

Extracted issues:
1. `httpx/_models.py`: The new implementation of the json() method may not handle non-UTF charsets as well as the previous version, which used self.text for decoding.

## encode/httpx#2909  Drop unneccessary `binascii` import

Human comments:
- `httpx/_multipart.py` (T-256): Oh, I see python 2 user 😄  ```suggestion             boundary = os.urandom(16).hex() ```

Extracted issues:
1. `httpx/_multipart.py`: The code for generating a hex string from random bytes can be simplified by using os.urandom(16).hex() instead of a manual join and format.
