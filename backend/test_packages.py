#!/usr/bin/env python3
"""
Package verification script to test AI and social media libraries
"""


def test_package_imports():
    """Test all required package imports"""
    results = {}

    # Test TextBlob
    try:
        from textblob import TextBlob

        test_blob = TextBlob("This is a test sentence.")
        results["textblob"] = {
            "status": "SUCCESS",
            "version": getattr(TextBlob, "__version__", "unknown"),
            "test": f"Sentiment: {test_blob.sentiment}",
        }
    except Exception as e:
        results["textblob"] = {"status": "FAILED", "error": str(e)}

    # Test Transformers
    try:
        import transformers

        results["transformers"] = {"status": "SUCCESS", "version": transformers.__version__}
    except Exception as e:
        results["transformers"] = {"status": "FAILED", "error": str(e)}

    # Test PyTorch
    try:
        import torch

        results["torch"] = {"status": "SUCCESS", "version": torch.__version__, "cuda_available": torch.cuda.is_available()}
    except Exception as e:
        results["torch"] = {"status": "FAILED", "error": str(e)}

    # Test Tweepy
    try:
        import tweepy

        results["tweepy"] = {"status": "SUCCESS", "version": tweepy.__version__}
    except Exception as e:
        results["tweepy"] = {"status": "FAILED", "error": str(e)}

    return results


def print_results(results):
    """Print formatted test results"""
    print("📦 Package Import Test Results")
    print("=" * 50)

    for package, result in results.items():
        status = result["status"]
        if status == "SUCCESS":
            print(f"✅ {package.upper()}: {status}")
            if "version" in result:
                print(f"   Version: {result['version']}")
            if "test" in result:
                print(f"   Test: {result['test']}")
            if "cuda_available" in result:
                print(f"   CUDA Available: {result['cuda_available']}")
        else:
            print(f"❌ {package.upper()}: {status}")
            print(f"   Error: {result['error']}")
        print()


if __name__ == "__main__":
    print("🚀 Testing Package Imports...")
    print()

    results = test_package_imports()
    print_results(results)

    # Summary
    successful = sum(1 for r in results.values() if r["status"] == "SUCCESS")
    total = len(results)

    print(f"📊 Summary: {successful}/{total} packages imported successfully")

    if successful == total:
        print("🎉 All packages are working correctly!")
    else:
        print("⚠️  Some packages have issues. Check the errors above.")
