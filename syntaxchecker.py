from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener
import sys
sys.path.append("lexerparser")
from DOTLexer import DOTLexer
from DOTParser import DOTParser


# Report lexical and syntactic errors
class DOTErrorListener(ErrorListener):
	def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
		if isinstance(recognizer, DOTLexer):
			print("Lexical Error", end=': ')
		elif isinstance(recognizer, DOTParser):
			print("Syntactic Error", end=': ')
		print("line %d, column %d: %s" %(line, column, msg))
		raise Exception()

	def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
		pass

	def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs):
		pass

	def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
		pass

# This is the core function
def check(dot):
	input = InputStream(dot)
	lexer = DOTLexer(input)
	stream = CommonTokenStream(lexer)
	parser = DOTParser(stream)

	lexer.removeErrorListeners()
	lexer.addErrorListener(DOTErrorListener())
	parser.removeErrorListeners()
	parser.addErrorListener(DOTErrorListener())

	try:
		tree = parser.graph()
	except:
		return False
	return True

if __name__ == '__main__':
	dot = '''
	digraph d {
	a->b;
	}
	'''
	res = check(dot)
	if res:
		print("No error")