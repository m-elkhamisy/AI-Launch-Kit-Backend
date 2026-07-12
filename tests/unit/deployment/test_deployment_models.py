from launchkit.deployment import DeploymentResult, DeploymentStatus


def test_deployment_result_preserves_claim_shape() -> None:
    deployment = DeploymentResult(
        chat_id="chat_1",
        project_id="project_1",
        deployment_id=None,
        live_url=None,
        claim_url="https://vercel.com/claim-deployment?code=abc",
        note="Transfer the project.",
    )

    payload = deployment.model_dump(by_alias=True, mode="json")
    assert deployment.status is DeploymentStatus.READY_TO_CLAIM
    assert payload["claimExpires"] == "24 hours"
