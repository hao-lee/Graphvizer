from .antlr4 import *
from .antlr4.error.ErrorListener import ErrorListener
from .lexerparser.DOTLexer import DOTLexer
from .lexerparser.DOTParser import DOTParser


# Report lexical and syntactic errors
class DOTErrorListener(ErrorListener):
	def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
		if isinstance(recognizer, DOTLexer):
			who = "Lexical Error:"
		elif isinstance(recognizer, DOTParser):
			who = "Syntactic Error:"
		raise Exception("%s line %d, column %d: %s" %(who, line, column, msg))

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
		return True, "Syntax check passed"
	except Exception as e:
		return False, str(e)

if __name__ == '__main__':
	dot = '''
	digraph d {
	a->b;
	}
	'''
	res = check(dot)
	if res:
		print("No error")
