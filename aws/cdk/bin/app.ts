#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { IngestionStack } from "../lib/ingestion-stack";

const app = new cdk.App();

new IngestionStack(app, "IngestionStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "eu-west-2",
  },
});
