# LangGraph Learning Notes

This repository contains my course notes and practice code while learning LangGraph.
It follows a simple progression from basic graph concepts to more advanced agent workflows, RAG systems, human review, streaming, and multi-agent design.

## What I Covered

- Introduction to LangGraph and basic ReAct style agents.
- Reflection and reflexion loops for improving model responses.
- Structured outputs with Pydantic and typed data.
- State management and message handling in graph workflows.
- Chatbots with tools and checkpointers.
- Human-in-the-loop workflows with interrupts and resume patterns.
- Retrieval-Augmented Generation (RAG) agents.
- Multi-agent architectures with supervisor routing and subgraphs.
- Streaming graph events and step-by-step execution.
- A first RAG project with a small end-to-end application.

## Folder Guide

- `1_Introduction/` and `1_introduction/` - first LangGraph and ReAct examples.
- `2_basic_reflection_system/` - a simple generate-and-reflect workflow.
- `2_reflection_agent/` - reflection agent practice.
- `3_structured_outputs/` - typed outputs and Pydantic-based examples.
- `4_reflexion_agent_system/` - reflexion loop with tool execution and revision.
- `5_state_deepdive/` - state handling, message flow, and retrieval examples.
- `6_react_agent/` - a full ReAct agent built as a graph.
- `7_chatbot/` - chatbot examples with tools and checkpointers.
- `8_human-in-the-loop/` - manual approval, resume, and multi-turn interaction.
- `9_RAG_agent/` - RAG notebooks with classification and multi-step reasoning.
- `10_multi_agent_architecture/` - subgraphs and supervisor-based multi-agent workflows.
- `11_streaming/` - streaming events and graph output inspection.
- `First_project_RAG/` - a small RAG project with app code and supporting assets.

## How To Use

1. Create and activate a Python virtual environment.
2. Install the dependencies from `requirements.txt`.
3. Open the notebooks or run the Python scripts in each folder.
4. Follow the folders in order if you want to study the course from beginner to advanced.

## Project Goal

The goal of this repository is to document my LangGraph learning journey in a clear and practical way.
Each folder is a small lesson or experiment that shows one part of the overall course.

## Main Focus

- Build simple agents first.
- Learn how graph state changes over time.
- Add tools, retrieval, and human feedback.
- Move toward multi-agent and production-style workflows.

## Requirements

See [requirements.txt](requirements.txt) for the full Python dependency list.
