import os

import anthropic
import pytest
from haystack.components.generators.utils import print_streaming_chunk
from haystack.dataclasses import StreamingChunk
from haystack.utils.auth import Secret

from haystack_integrations.components.generators.anthropic import AnthropicGenerator


class TestAnthropicGenerator:
    def test_init_default(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
        component = AnthropicGenerator()
        assert component.client.api_key == "test-api-key"
        assert component.model == "claude-sonnet-4-20250514"
        assert component.streaming_callback is None
        assert not component.generation_kwargs

    def test_init_fail_wo_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="None of the .* environment variables are set"):
            AnthropicGenerator()

    def test_init_with_parameters(self):
        component = AnthropicGenerator(
            api_key=Secret.from_token("test-api-key"),
            model="claude-sonnet-4-20250514",
            streaming_callback=print_streaming_chunk,
            generation_kwargs={"max_tokens": 10, "some_test_param": "test-params"},
        )
        assert component.client.api_key == "test-api-key"
        assert component.model == "claude-sonnet-4-20250514"
        assert component.streaming_callback is print_streaming_chunk
        assert component.generation_kwargs == {"max_tokens": 10, "some_test_param": "test-params"}

    def test_to_dict_default(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
        component = AnthropicGenerator()
        data = component.to_dict()
        assert data == {
            "type": "haystack_integrations.components.generators.anthropic.generator.AnthropicGenerator",
            "init_parameters": {
                "api_key": {"env_vars": ["ANTHROPIC_API_KEY"], "strict": True, "type": "env_var"},
                "model": "claude-sonnet-4-20250514",
                "streaming_callback": None,
                "system_prompt": None,
                "generation_kwargs": {},
                "timeout": None,
                "max_retries": None,
            },
        }

    def test_to_dict_with_parameters(self, monkeypatch):
        monkeypatch.setenv("ENV_VAR", "test-api-key")
        component = AnthropicGenerator(
            api_key=Secret.from_env_var("ENV_VAR"),
            streaming_callback=print_streaming_chunk,
            system_prompt="test-prompt",
            generation_kwargs={"max_tokens": 10, "some_test_param": "test-params"},
            timeout=10.0,
            max_retries=1,
        )
        data = component.to_dict()
        assert data == {
            "type": "haystack_integrations.components.generators.anthropic.generator.AnthropicGenerator",
            "init_parameters": {
                "api_key": {"env_vars": ["ENV_VAR"], "strict": True, "type": "env_var"},
                "model": "claude-sonnet-4-20250514",
                "system_prompt": "test-prompt",
                "streaming_callback": "haystack.components.generators.utils.print_streaming_chunk",
                "generation_kwargs": {"max_tokens": 10, "some_test_param": "test-params"},
                "timeout": 10.0,
                "max_retries": 1,
            },
        }

    def test_from_dict(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-api-key")
        data = {
            "type": "haystack_integrations.components.generators.anthropic.generator.AnthropicGenerator",
            "init_parameters": {
                "api_key": {"env_vars": ["ANTHROPIC_API_KEY"], "strict": True, "type": "env_var"},
                "model": "claude-sonnet-4-20250514",
                "system_prompt": "test-prompt",
                "streaming_callback": "haystack.components.generators.utils.print_streaming_chunk",
                "generation_kwargs": {"max_tokens": 10, "some_test_param": "test-params"},
                "timeout": None,
                "max_retries": None,
            },
        }
        component = AnthropicGenerator.from_dict(data)
        assert component.model == "claude-sonnet-4-20250514"
        assert component.streaming_callback is print_streaming_chunk
        assert component.system_prompt == "test-prompt"
        assert component.generation_kwargs == {"max_tokens": 10, "some_test_param": "test-params"}
        assert component.api_key == Secret.from_env_var("ANTHROPIC_API_KEY")
        assert component.timeout is None
        assert component.max_retries is None

    def test_from_dict_fail_wo_env_var(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        data = {
            "type": "haystack_integrations.components.generators.anthropic.generator.AnthropicGenerator",
            "init_parameters": {
                "api_key": {"env_vars": ["ANTHROPIC_API_KEY"], "strict": True, "type": "env_var"},
                "model": "claude-sonnet-4-20250514",
                "system_prompt": "test-prompt",
                "streaming_callback": "haystack.components.generators.utils.print_streaming_chunk",
                "generation_kwargs": {"max_tokens": 10, "some_test_param": "test-params"},
                "timeout": None,
                "max_retries": None,
            },
        }
        with pytest.raises(ValueError, match="None of the .* environment variables are set"):
            AnthropicGenerator.from_dict(data)

    def test_run(self, mock_chat_completion):
        component = AnthropicGenerator(api_key=Secret.from_token("test-api-key"))
        response = component.run("What is the capital of France?")

        # check that the component returns the correct ChatMessage response
        assert isinstance(response, dict)
        assert "replies" in response
        assert "meta" in response
        assert isinstance(response["replies"], list)
        assert isinstance(response["meta"], list)
        assert len(response["replies"]) == 1
        assert len(response["meta"]) == 1
        assert [isinstance(reply, str) for reply in response["replies"]]
        assert [isinstance(meta, dict) for meta in response["meta"]]

    def test_run_with_params(self, mock_chat_completion):
        component = AnthropicGenerator(
            api_key=Secret.from_token("test-api-key"), generation_kwargs={"max_tokens": 10, "temperature": 0.5}
        )
        response = component.run("What is the capital of France?")

        # check that the component calls the Anthropic API with the correct parameters
        _, kwargs = mock_chat_completion.call_args
        assert kwargs["max_tokens"] == 10
        assert kwargs["temperature"] == 0.5

        # check that the component returns the correct response
        assert isinstance(response, dict)
        assert "replies" in response
        assert isinstance(response["replies"], list)
        assert len(response["replies"]) == 1
        assert [isinstance(reply, str) for reply in response["replies"]]
        assert "meta" in response
        assert isinstance(response["meta"], list)
        assert len(response["meta"]) == 1
        assert [isinstance(meta, dict) for meta in response["meta"]]

    def test_run_extended_thinking(self, mock_chat_completion_extended_thinking):
        component = AnthropicGenerator(api_key=Secret.from_token("test-api-key"))
        response = component.run("What is the capital of France?")

        # check that the component returns the correct ChatMessage response
        assert isinstance(response, dict)
        assert "replies" in response
        assert "meta" in response
        assert isinstance(response["replies"], list)
        assert isinstance(response["meta"], list)
        assert len(response["replies"]) == 1
        assert len(response["meta"]) == 1
        assert [isinstance(reply, str) for reply in response["replies"]]
        assert [isinstance(meta, dict) for meta in response["meta"]]
        assert response["replies"][0] == "<thinking>This is a thinking part!</thinking>\n\nHello, world!"

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY", None),
        reason="Export an env var called ANTHROPIC_API_KEY containing the Anthropic API key to run this test.",
    )
    @pytest.mark.integration
    def test_live_run_wrong_model(self):
        component = AnthropicGenerator(model="something-obviously-wrong")
        with pytest.raises(anthropic.NotFoundError):
            component.run("What is the capital of France?")

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY", None),
        reason="Export an env var called ANTHROPIC_API_KEY containing the Anthropic API key to run this test.",
    )
    @pytest.mark.integration
    def test_default_inference_params(self):
        client = AnthropicGenerator()
        response = client.run("What is the capital of France?")

        assert "replies" in response, "Response does not contain 'replies' key"
        replies = response["replies"]
        assert isinstance(replies, list), "Replies is not a list"
        assert len(replies) > 0, "No replies received"

        first_reply = replies[0]
        assert isinstance(first_reply, str), "First reply is not a str instance"
        assert first_reply, "First reply has no content"
        assert "paris" in first_reply.lower(), "First reply does not contain 'paris'"

        assert "meta" in response, "Response does not contain 'meta' key"
        meta = response["meta"]
        assert isinstance(meta, list), "Meta is not a list"
        assert len(meta) > 0, "No meta received"
        assert isinstance(meta[0], dict), "First meta is not a dict instance"

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY", None),
        reason="Export an env var called ANTHROPIC_API_KEY containing the Anthropic API key to run this test.",
    )
    @pytest.mark.integration
    def test_default_inference_with_streaming(self):
        streaming_callback_called = False
        paris_found_in_response = False

        def streaming_callback(chunk: StreamingChunk):
            nonlocal streaming_callback_called, paris_found_in_response
            streaming_callback_called = True
            assert isinstance(chunk, StreamingChunk)
            assert chunk.content is not None
            if not paris_found_in_response:
                paris_found_in_response = "paris" in chunk.content.lower()

        client = AnthropicGenerator(streaming_callback=streaming_callback)
        response = client.run("What is the capital of France?")

        assert streaming_callback_called, "Streaming callback was not called"
        assert paris_found_in_response, "The streaming callback response did not contain 'paris'"
        replies = response["replies"]
        assert isinstance(replies, list), "Replies is not a list"
        assert len(replies) > 0, "No replies received"

        first_reply = replies[0]
        assert isinstance(first_reply, str), "First reply is not a str instance"
        assert first_reply, "First reply has no content"
        assert "paris" in first_reply.lower(), "First reply does not contain 'paris'"

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY", None),
        reason="Export an env var called ANTHROPIC_API_KEY containing the Anthropic API key to run this test.",
    )
    @pytest.mark.integration
    def test_extended_thinking_mode(self):
        client = AnthropicGenerator(
            model="claude-sonnet-4-20250514",
            generation_kwargs={"thinking": {"type": "enabled", "budget_tokens": 1024}, "max_tokens": 1536},
        )
        response = client.run("What is the capital of France?")

        assert "replies" in response, "Response does not contain 'replies' key"
        replies = response["replies"]
        assert isinstance(replies, list), "Replies is not a list"
        assert len(replies) > 0, "No replies received"

        first_reply = replies[0]
        assert isinstance(first_reply, str), "First reply is not a str instance"
        assert first_reply, "First reply has no content"
        assert "paris" in first_reply.lower(), "First reply does not contain 'paris'"
        assert "<thinking>" in first_reply, "First reply does not contain a thinking block"
        assert "</thinking>" in first_reply, "First reply does not contain a closing thinking block"

        assert "meta" in response, "Response does not contain 'meta' key"
        meta = response["meta"]
        assert isinstance(meta, list), "Meta is not a list"
        assert len(meta) > 0, "No meta received"
        assert isinstance(meta[0], dict), "First meta is not a dict instance"

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY", None),
        reason="Export an env var called ANTHROPIC_API_KEY containing the Anthropic API key to run this test.",
    )
    @pytest.mark.integration
    def test_extended_thinking_mode_with_streaming(self):
        streaming_callback_called = False
        paris_found_in_response = False
        thinking_start_tag_found = False
        thinking_end_tag_found = False

        def streaming_callback(chunk: StreamingChunk):
            nonlocal streaming_callback_called, paris_found_in_response
            nonlocal thinking_start_tag_found, thinking_end_tag_found
            streaming_callback_called = True
            assert isinstance(chunk, StreamingChunk)
            assert chunk.content is not None
            if not paris_found_in_response:
                paris_found_in_response = "paris" in chunk.content.lower()
            if not thinking_start_tag_found:
                thinking_start_tag_found = "<thinking>" in chunk.content
            if not thinking_end_tag_found:
                thinking_end_tag_found = "</thinking>" in chunk.content

        client = AnthropicGenerator(
            model="claude-sonnet-4-20250514",
            generation_kwargs={"thinking": {"type": "enabled", "budget_tokens": 1024}, "max_tokens": 1536},
            streaming_callback=streaming_callback,
        )
        response = client.run("What is the capital of France?")

        assert streaming_callback_called, "Streaming callback was not called"
        assert paris_found_in_response, "The streaming callback response did not contain 'paris'"
        replies = response["replies"]
        assert isinstance(replies, list), "Replies is not a list"
        assert len(replies) > 0, "No replies received"

        first_reply = replies[0]
        assert isinstance(first_reply, str), "First reply is not a str instance"
        assert first_reply, "First reply has no content"
        assert "paris" in first_reply.lower(), "First reply does not contain 'paris'"
        assert "<thinking>" in first_reply, "First reply does not contain a thinking block"
        assert "</thinking>" in first_reply, "First reply does not contain a closing thinking block"
        assert thinking_start_tag_found, "The streaming callback response did not contain a thinking start tag"
        assert thinking_end_tag_found, "The streaming callback response did not contain a thinking end tag"

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY", None),
        reason="Export an env var called ANTHROPIC_API_KEY containing the Anthropic API key to run this test.",
    )
    @pytest.mark.integration
    def test_extended_thinking_mode_with_streaming_include_thinking_false(self):
        streaming_callback_called = False
        paris_found_in_response = False
        thinking_start_tag_found = False
        thinking_end_tag_found = False

        def streaming_callback(chunk: StreamingChunk):
            nonlocal streaming_callback_called, paris_found_in_response
            nonlocal thinking_start_tag_found, thinking_end_tag_found
            streaming_callback_called = True
            assert isinstance(chunk, StreamingChunk)
            assert chunk.content is not None
            if not paris_found_in_response:
                paris_found_in_response = "paris" in chunk.content.lower()
            if not thinking_start_tag_found:
                thinking_start_tag_found = "<thinking>" in chunk.content
            if not thinking_end_tag_found:
                thinking_end_tag_found = "</thinking>" in chunk.content

        client = AnthropicGenerator(
            model="claude-sonnet-4-20250514",
            generation_kwargs={
                "thinking": {"type": "enabled", "budget_tokens": 1024},
                "max_tokens": 1536,
                "include_thinking": False,
            },
            streaming_callback=streaming_callback,
        )
        response = client.run("What is the capital of France?")

        assert streaming_callback_called, "Streaming callback was not called"
        assert paris_found_in_response, "The streaming callback response did not contain 'paris'"
        replies = response["replies"]
        assert isinstance(replies, list), "Replies is not a list"
        assert len(replies) > 0, "No replies received"

        first_reply = replies[0]
        assert isinstance(first_reply, str), "First reply is not a str instance"
        assert first_reply, "First reply has no content"
        assert "paris" in first_reply.lower(), "First reply does not contain 'paris'"
        assert "<thinking>" not in first_reply, "First reply does contain a thinking block"
        assert "</thinking>" not in first_reply, "First reply does contain a closing thinking block"
        assert not thinking_start_tag_found, "The streaming callback response did contain a thinking start tag"
        assert not thinking_end_tag_found, "The streaming callback response did contain a thinking end tag"
