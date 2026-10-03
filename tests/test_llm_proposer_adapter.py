from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_contracts import CognitiveRequest
from grandnexus.multiagent.llm_proposer import LLMCallBudget, StructuredLLMProposer


class Message:
    content = '{"claim":"The robot cannot open the door","evidence":["negative observation"],"confidence":0.72,"action_intent":"describe"}'


class Choice:
    message = Message()


class Response:
    choices = [Choice()]


class Completions:
    def create(self, **kwargs):
        assert kwargs['model'] == 'gpt-5-mini'
        assert kwargs['response_format']['json_schema']['strict'] is True
        assert kwargs['max_completion_tokens'] == 300
        assert 'action_intent' in kwargs['response_format']['json_schema']['schema']['properties']
        return Response()


class FakeClient:
    chat = type('Chat', (), {'completions': Completions()})()


def main():
    budget = LLMCallBudget(max_calls=1)
    proposer = StructuredLLMProposer(budget=budget, client=FakeClient())
    result = proposer.propose(CognitiveRequest('Inspect the semantic graph'))
    assert result.agent_id == 'llm-proposer'
    assert result.confidence == 0.72
    assert result.action_requested is False
    assert result.action_intent == 'describe'
    assert budget.calls == 1
    try:
        proposer.propose(CognitiveRequest('Second call'))
    except RuntimeError as exc:
        assert 'budget' in str(exc)
    else:
        raise AssertionError('budget was not enforced')
    print({'agent': result.agent_id, 'confidence': result.confidence, 'calls': budget.calls})


if __name__ == '__main__':
    main()
