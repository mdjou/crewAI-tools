import os
import json
import weaviate
from pydantic import BaseModel, Field
from typing import Type, Optional
from crewai.tools import BaseTool

from weaviate.classes.config import Configure, Vectorizers
from weaviate.classes.init import Auth


class WeaviateToolSchema(BaseModel):
    """Input for WeaviateTool."""

    query: str = Field(
        ...,
        description="The query to search retrieve relevant information from the Weaviate database. Pass only the query, not the question.",
    )


class WeaviateVectorSearchTool(BaseTool):
    """Tool to search the Weaviate database"""

    name: str = "WeaviateVectorSearchTool"
    description: str = "A tool to search the Weaviate database for relevant information on internal documents."
    args_schema: Type[BaseModel] = WeaviateToolSchema
    query: Optional[str] = None

    vectorizer: Optional[Vectorizers] = Field(
        default=Configure.Vectorizer.text2vec_openai(
            model="nomic-embed-text",
        )
    )
    generative_model: Optional[str] = Field(
        default=Configure.Generative.openai(
            model="gpt-4o",
        ),
    )
    collection_name: Optional[str] = None
    limit: Optional[int] = Field(default=3)
    headers: Optional[dict] = Field(
        default={"X-OpenAI-Api-Key": os.environ["OPENAI_API_KEY"]}
    )
    weaviate_cluster_url: str = Field(
        ...,
        description="The URL of the Weaviate cluster",
    )
    weaviate_api_key: str = Field(
        ...,
        description="The API key for the Weaviate cluster",
    )

    def _run(self, query: str) -> str:
        """Search the Weaviate database

        Args:
            query (str): The query to search retrieve relevant information from the Weaviate database. Pass only the query as a string, not the question.

        Returns:
            str: The result of the search query
        """

        if not self.weaviate_cluster_url or not self.weaviate_api_key:
            raise ValueError("WEAVIATE_URL or WEAVIATE_API_KEY is not set")

        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=self.weaviate_cluster_url,
            auth_credentials=Auth.api_key(self.weaviate_api_key),
            headers=self.headers,
        )
        internal_docs = client.collections.get(self.collection_name)

        if not internal_docs:
            internal_docs = client.collections.create(
                name=self.collection_name,
                vectorizer_config=self.vectorizer,
                generative_config=self.generative_model,
            )

        response = internal_docs.query.near_text(
            query=query,
            limit=self.limit,
        )
        json_response = ""
        for obj in response.objects:
            json_response += json.dumps(obj.properties, indent=2)

        client.close()
        return json_response
